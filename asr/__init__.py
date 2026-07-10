# asr/__init__.py
# 识别引擎工厂：按 kind 返回对应引擎实例。
#   - "offline" / "funasr" / "local"  -> FunASROnnxEngine（默认，纯离线、torch-free）
#   - "cloud"   / "xunfei"            -> XunfeiEngine（云端讯飞，需密钥）
from .base import ASREngine
from .funasr_onnx_engine import FunASROnnxEngine


class XunfeiEngine(ASREngine):
    """云端讯飞引擎：复用 backend.xf_asr（需 Xunfei 密钥）。"""
    name = "xunfei"

    def _load_impl(self):
        # 模型即云端服务，无需本地加载；仅校验 backend 可用。
        try:
            import backend  # noqa: F401
        except Exception as e:
            raise RuntimeError("无法加载 backend（xf_asr）：" + str(e))

    def transcribe(self, wav_path: str) -> str:
        self.load()
        import backend
        rate, samples = self.read_wav(wav_path)
        import wave as _w
        buf = __import__("io").BytesIO()
        with _w.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(samples.tobytes())
        pcm = backend.wav_bytes_to_pcm16k(buf.getvalue())
        return backend.xf_asr(pcm)


_ENGINES = {
    "offline": FunASROnnxEngine,
    "funasr": FunASROnnxEngine,
    "local": FunASROnnxEngine,
    "cloud": XunfeiEngine,
    "xunfei": XunfeiEngine,
}


def get_asr_engine(kind: str = "offline", model_dir: str = None) -> ASREngine:
    cls = _ENGINES.get(kind, FunASROnnxEngine)
    return cls(model_dir=model_dir)


__all__ = ["ASREngine", "FunASROnnxEngine", "XunfeiEngine", "get_asr_engine"]
