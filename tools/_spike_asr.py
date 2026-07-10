# _spike_asr.py  (临时验证脚本，验证通过后删除)
# 目的：验证「FunASR Paraformer ONNX + onnxruntime(sherpa-onnx)」能在本机纯离线、torch-free 跑通中文识别，
#       并测量 CPU 实时率(RTF = 计算耗时 / 音频时长，<1 即比实时快)。
import os
import sys
import time
import glob
import tarfile
import wave

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from asr import FunASROnnxEngine

MODELS = os.path.join(ROOT, "assets", "asr_models")
ARCHIVE = os.path.join(MODELS, "paraformer-zh.tar.bz2")


def extract_once():
    # 找到已解压的模型目录（含 model.onnx 或 *.onnx + tokens.txt）
    for sub in sorted(glob.glob(os.path.join(MODELS, "*"))):
        if os.path.isdir(sub) and glob.glob(os.path.join(sub, "*.onnx")):
            return sub
    if os.path.exists(ARCHIVE):
        print(f"[解压] {ARCHIVE} ...")
        with tarfile.open(ARCHIVE, "r:bz2") as tf:
            tf.extractall(MODELS)
        for sub in sorted(glob.glob(os.path.join(MODELS, "*"))):
            if os.path.isdir(sub) and glob.glob(os.path.join(sub, "*.onnx")):
                return sub
    raise RuntimeError("未找到模型：请先下载 paraformer-zh.tar.bz2 并放置于 assets/asr_models/")


def main():
    model_dir = extract_once()
    print(f"[模型目录] {model_dir}")
    onnx = sorted(glob.glob(os.path.join(model_dir, "*.onnx")))
    toks = sorted(glob.glob(os.path.join(model_dir, "tokens.txt")))
    print(f"[模型文件] onnx={len(onnx)} tokens={len(toks)}")

    eng = FunASROnnxEngine(model_dir=model_dir)
    t0 = time.time()
    eng.load()
    print(f"[加载耗时] {time.time()-t0:.2f}s")

    wavs = sorted(glob.glob(os.path.join(model_dir, "test_wavs", "*.wav")))
    if not wavs:
        wavs = sorted(glob.glob(os.path.join(model_dir, "**", "*.wav"), recursive=True))
    print(f"[测试样本] {len(wavs)} 个")

    total_audio = 0.0
    total_cpu = 0.0
    for w in wavs[:5]:  # 最多测 5 个，避免过度耗时
        with wave.open(w, "rb") as wf:
            rate = wf.getframerate()
            n = wf.getnframes()
        dur = n / rate
        total_audio += dur
        t0 = time.time()
        text = eng.transcribe(w)
        dt = time.time() - t0
        total_cpu += dt
        rtf = dt / dur if dur > 0 else 0
        print(f"  - {os.path.basename(w)} ({dur:.1f}s) -> {text!r}  [RTF={rtf:.2f}]")

    if total_audio > 0:
        print(f"[整体] 音频 {total_audio:.1f}s / CPU {total_cpu:.1f}s / 平均 RTF={total_cpu/total_audio:.2f}")
        print("[结论] RTF<1 表示比实时更快，离线识别可行。" if (total_cpu/total_audio) < 1 else "[结论] RTF>=1，CPU 偏慢，需调优线程数或换更小模型。")
    print("SPIKE_OK")


if __name__ == "__main__":
    main()
