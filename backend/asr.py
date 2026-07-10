#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语音识别（ASR）相关：讯飞云端、本地 FunASR(torch)、离线引擎路由与音频转换。"""
import os
import sys
import json
import time
import base64
import hashlib
import hmac
import datetime
import tempfile
import threading
from urllib.parse import urlencode

from . import _state


# ============================ 引擎选择 ============================
def set_asr_engine(choice: str):
    """运行时切换识别引擎（供设置面板调用），同步更新环境变量与共享状态，下次转写即生效。

    choice ∈ {auto, offline, xunfei, funasr}
    """
    _state.ASR_ENGINE_CHOICE = (choice or "auto").lower()
    if _state.ASR_ENGINE_CHOICE not in ("auto", "offline", "xunfei", "funasr"):
        _state.ASR_ENGINE_CHOICE = "auto"
    os.environ["ASR_ENGINE"] = _state.ASR_ENGINE_CHOICE
    return _state.ASR_ENGINE_CHOICE


def resolve_asr_engine() -> str:
    """返回 transcribe_audio 当前会使用的识别引擎：xunfei / offline_onnx / funasr / none。"""
    e = _state.ASR_ENGINE_CHOICE
    if e == "xunfei":
        return "xunfei" if _state.ASR_READY else "none"
    if e == "funasr":
        return "funasr" if _state.FUNASR_AVAILABLE else "none"
    if e == "offline":
        return "offline_onnx" if _state.OFFLINE_ONNX_AVAILABLE else "none"
    # auto：云端优先，其次离线 ONNX，再 torch FunASR
    if _state.ASR_READY:
        return "xunfei"
    if _state.OFFLINE_ONNX_AVAILABLE:
        return "offline_onnx"
    if _state.FUNASR_AVAILABLE:
        return "funasr"
    return "none"


# ============================ 离线 FunASR(torch) ============================
def _get_funasr_model():
    if _state._FUNASR_MODEL is None:
        if _state.funasr is None:
            raise RuntimeError("未安装 funasr，请先 pip install funasr")
        from funasr import AutoModel
        if _state.OFFLINE_ASR_MODEL:
            _state._FUNASR_MODEL = AutoModel(model=_state.OFFLINE_ASR_MODEL, device="cpu")
        else:
            _state._FUNASR_MODEL = AutoModel(
                model="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                model_revision="v2.0.4",
                vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
                vad_model_revision="v2.0.4",
                punc_model="iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
                punc_model_revision="v2.0.4",
                device="cpu",
            )
    return _state._FUNASR_MODEL


def get_offline_engine():
    """懒加载并缓存 torch-free 的 FunASR-ONNX 离线引擎（零 torch、零 sherpa）。"""
    if _state._OFFLINE_ENGINE is None:
        from asr import get_asr_engine
        _state._OFFLINE_ENGINE = get_asr_engine("offline", model_dir=_state.OFFLINE_MODEL_DIR)
    return _state._OFFLINE_ENGINE


def run_funasr(raw: bytes, suffix: str) -> str:
    wav = ffmpeg_to_wav16k(raw, suffix)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tf.write(wav)
        wav_path = tf.name
    try:
        model = _get_funasr_model()
        res = model.generate(input=wav_path, batch_size_s=300)
        if res and isinstance(res, list):
            first = res[0]
            return first.get("text", "") if isinstance(first, dict) else str(first)
        return ""
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass


# ============================ 讯飞 ASR ============================
def _now_gmt():
    return datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")


def build_xf_url():
    host = "iat-api.xfyun.cn"
    path = "/v2/iat"
    date = _now_gmt()
    signature_origin = "host: " + host + "\n"
    signature_origin += "date: " + date + "\n"
    signature_origin += "GET " + path + " HTTP/1.1"
    signature_sha = hmac.new(
        _state.XF_API_SECRET.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature_b64 = base64.b64encode(signature_sha).decode("utf-8")
    authorization_origin = (
        'api_key="%s", algorithm="hmac-sha256", '
        'headers="host date request-line", signature="%s"'
        % (_state.XF_API_KEY, signature_b64)
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
    query = urlencode({"authorization": authorization, "date": date, "host": host})
    return "wss://" + host + path + "?" + query


def _frames_from_pcm(pcm: bytes):
    size = 1280
    n = len(pcm)
    idx = 0
    while idx < n:
        chunk = pcm[idx: idx + size]
        status = 1 if idx > 0 else 0
        if idx + size >= n:
            status = 2
        yield base64.b64encode(chunk).decode("utf-8"), status
        idx += size


def xf_asr(pcm_bytes: bytes) -> str:
    if not _state.ASR_READY:
        raise RuntimeError("ASR 未配置（缺少讯飞密钥或未安装 websocket-client）")
    url = build_xf_url()
    business = {
        "language": "zh_cn",
        "domain": "iat",
        "accent": "henan",
        "vad_eos": 1000,
        "dwa": "wpgs",
    }
    result_text = []
    error = {}

    def on_message(ws, message):
        data = json.loads(message)
        code = data.get("code")
        if code != 0:
            error["msg"] = data.get("message", "未知错误")
            ws.close()
            return
        payload = data.get("payload", {})
        if "result" not in payload:
            return
        txt_b64 = payload["result"]["text"]
        d = json.loads(base64.b64decode(txt_b64).decode("utf-8"))
        for ws_item in d.get("ws", []):
            for cw in ws_item.get("cw", []):
                result_text.append(cw.get("w", ""))
        if payload.get("result", {}).get("status") == 2:
            ws.close()

    def on_error(ws, err):
        error["msg"] = str(err)

    def on_close(ws, *a):
        pass

    ws = _state.websocket.WebSocketApp(url, on_message=on_message, on_error=on_error, on_close=on_close)

    def run_send():
        time.sleep(0.5)
        first_b64, _ = next(_frames_from_pcm(pcm_bytes))
        ws.send(json.dumps({
            "common": {"app_id": _state.XF_APPID},
            "business": business,
            "data": {"status": 0, "format": "audio/L16;rate=16000",
                     "encoding": "raw", "audio": first_b64},
        }))
        started = False
        for b64, status in _frames_from_pcm(pcm_bytes):
            if not started:
                started = True
                continue
            ws.send(json.dumps({"data": {"status": status, "audio": b64}}))
            time.sleep(0.04)

    t = threading.Thread(target=run_send, daemon=True)
    t.start()
    ws.run_forever(sslopt={"cert_reqs": 0})
    t.join(timeout=2)
    if error:
        raise RuntimeError("讯飞 ASR 错误：" + error.get("msg", "未知"))
    return "".join(result_text).strip()


# ============================ FFmpeg 转换 ============================
def ffmpeg_to_pcm16k_mono(raw: bytes, suffix: str) -> bytes:
    tmp_in = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp_in.write(raw)
    tmp_in.close()
    tmp_wav = tmp_in.name + ".wav"
    try:
        import subprocess
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_in.name, "-ar", "16000", "-ac", "1",
             "-acodec", "pcm_s16le", tmp_wav],
            check=True, capture_output=True,
        )
        with open(tmp_wav, "rb") as f:
            wav = f.read()
        return wav[44:] if wav[:4] == b"RIFF" else wav
    finally:
        for p in (tmp_in.name, tmp_wav):
            try:
                os.unlink(p)
            except OSError:
                pass


def ffmpeg_to_wav16k(raw: bytes, suffix: str) -> bytes:
    import subprocess
    tmp_in = tempfile.NamedTemporaryFile(suffix=suffix or ".webm", delete=False)
    tmp_in.write(raw)
    tmp_in.close()
    tmp_wav = tmp_in.name + ".wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_in.name, "-ar", "16000", "-ac", "1",
             "-acodec", "pcm_s16le", tmp_wav],
            check=True, capture_output=True,
        )
        with open(tmp_wav, "rb") as f:
            return f.read()
    finally:
        for p in (tmp_in.name, tmp_wav):
            try:
                os.unlink(p)
            except OSError:
                pass


def wav_bytes_to_pcm16k(wav_bytes: bytes) -> bytes:
    """从 WAV 字节中剥离 44 字节头，得到 16k/16bit 单声道 PCM。"""
    if wav_bytes[:4] == b"RIFF":
        return wav_bytes[44:]
    return wav_bytes


# ============================ 统一转写入口 ============================
def transcribe_audio(raw: bytes, suffix: str = ".wav") -> dict:
    """音频字节 -> 识别文本。返回 {'text':..., 'source':...}。

    引擎优先级（auto 模式下）：
      1. 讯飞云端（已配置密钥）
      2. 本地 FunASR-ONNX（已内置模型，纯 CPU、零上传）  ← v2.0 默认离线
      3. 本地 FunASR(torch)（需 pip install funasr）
    可用 ASR_ENGINE 环境变量强制指定某一引擎。
    """
    if not raw:
        raise ValueError("音频内容为空")
    engine = resolve_asr_engine()
    if engine == "xunfei":
        try:
            pcm = ffmpeg_to_pcm16k_mono(raw, suffix)
            text = xf_asr(pcm)
        except Exception as e:
            raise RuntimeError("识别失败：" + str(e))
        if not text:
            raise RuntimeError("未识别出文字，请靠近麦克风重试")
        return {"text": text, "source": "xfyun"}
    if engine == "offline_onnx":
        try:
            eng = get_offline_engine()
            text = eng.transcribe_bytes(raw, suffix or "wav")
        except Exception as e:
            raise RuntimeError("离线 FunASR 识别失败：" + str(e))
        if not text:
            raise RuntimeError("未识别出文字，请靠近麦克风重试")
        return {"text": text, "source": "offline_onnx"}
    if engine == "funasr":
        try:
            text = run_funasr(raw, suffix)
        except Exception as e:
            raise RuntimeError("离线 FunASR 识别失败：" + str(e))
        if not text:
            raise RuntimeError("未识别出文字，请靠近麦克风重试")
        return {"text": text, "source": "offline_funasr"}
    raise RuntimeError(
        "ASR 未配置：请在 .env 填入讯飞 APPID/APIKey/APISecret，"
        "或将离线模型放到 assets/asr_models/ 下启用本地离线识别"
    )
