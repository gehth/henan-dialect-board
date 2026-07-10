# asr/base.py
# 识别引擎抽象基类：所有后端（离线 FunASR-ONNX / 云端讯飞 / 演示词库）统一接口。
# 设计要点：
#   - 懒加载：load() 首次调用才真正载入模型，不拖慢主窗口启动（沿用 v1 懒加载思路）。
#   - 输入兼容：transcribe(wav_path) 识别本地 wav 文件；transcribe_bytes(raw, suffix) 兼容内存音频字节。
#   - 流式可选：stream_start / stream_feed 供后续"边说边出"扩展，默认不实现。
import os
import sys
import glob
import tempfile
import wave


class ASREngine:
    name = "base"

    def __init__(self, model_dir: str = None):
        self._loaded = False
        self.model_dir = model_dir or self.default_model_dir()

    @staticmethod
    def default_model_dir() -> str:
        """默认模型目录：优先 exe 同目录/assets，否则脚本目录/assets。"""
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        # asr 包位于项目根/asr 或 _MEIPASS/asr；assets 与 asr 同级
        cand = os.path.join(os.path.dirname(base), "assets", "asr_models")
        if os.path.isdir(cand):
            return cand
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "asr_models")

    # ---- 生命周期 ----
    def load(self):
        if self._loaded:
            return
        self._load_impl()
        self._loaded = True

    def unload(self):
        self._unload_impl()
        self._loaded = False

    def _load_impl(self):
        pass

    def _unload_impl(self):
        pass

    # ---- 识别接口 ----
    def transcribe(self, wav_path: str) -> str:
        """识别本地 wav 文件，返回文本。"""
        raise NotImplementedError

    def transcribe_bytes(self, raw: bytes, suffix: str = "wav") -> str:
        """识别内存中的音频字节（兼容录音器产出的 wav）。写出临时文件后调用 transcribe。"""
        self.load()
        import numpy as np  # noqa
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(raw)
        tmp.close()
        try:
            return self.transcribe(tmp.name)
        finally:
            try:
                os.remove(tmp.name)
            except Exception:
                pass

    # ---- 流式（可选，默认不实现）----
    def stream_start(self):
        raise NotImplementedError(f"{self.name} 不支持流式识别")

    def stream_feed(self, chunk: bytes) -> str:
        raise NotImplementedError(f"{self.name} 不支持流式识别")

    # ---- 工具 ----
    @staticmethod
    def read_wav(path: str):
        """读 wav 返回 (sample_rate, int16 numpy array)。"""
        import numpy as np
        with wave.open(path, "rb") as w:
            rate = w.getframerate()
            n = w.getnframes()
            data = w.readframes(n)
        samples = np.frombuffer(data, dtype=np.int16)
        return rate, samples
