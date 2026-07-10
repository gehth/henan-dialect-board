# asr/funasr_onnx_engine.py
# 离线识别引擎（v2.0 默认）：加载 FunASR Paraformer 官方导出的 ONNX 模型（单文件
# model.int8.onnx），用 torch-free 的 onnxruntime 运行时做纯 CPU 推理。
#
# 为什么这样选：FunASR 完整版依赖 torch（~1GB+），直接塞进 onedir 包会让体积爆炸；
# 官方边缘部署方案即「导出 ONNX + onnxruntime」。本引擎直接加载 FunASR 导出的 Paraformer
# ONNX（输入 speech[B,T,560]，输出 logits/token_num/us_alphas/us_cif_peak），自行完成
# fbank 特征 + CMVN + LFR 窗 + 推理 + 贪心解码，零 torch、零 sherpa 依赖。
#
# 推理流程对齐官方 test-paraformer-onnx.py（kaldi_native_fbank 提特征、am.mvn 做 CMVN）。
import os
import glob

import numpy as np

from .base import ASREngine


class FunASROnnxEngine(ASREngine):
    name = "funasr_onnx"

    # ---- 模型定位 ----
    def _resolve_model(self):
        d = self.model_dir
        candidates = [d] + [
            s for s in sorted(glob.glob(os.path.join(d, "*"))) if os.path.isdir(s)
        ]
        for c in candidates:
            onnxs = sorted(glob.glob(os.path.join(c, "*.onnx")))
            toks = glob.glob(os.path.join(c, "tokens.txt"))
            mvn = glob.glob(os.path.join(c, "am.mvn"))
            if onnxs and toks and mvn:
                return onnxs[0], toks[0], mvn[0]
        raise RuntimeError(
            f"未在 {self.model_dir} 找到 Paraformer ONNX 模型（需 *.onnx + tokens.txt + am.mvn）。"
        )

    # ---- 加载 ----
    def _load_impl(self):
        import onnxruntime as ort
        import kaldi_native_fbank as knf

        model, tokens, mvn = self._resolve_model()
        self._model_path = model
        self._mvn_path = mvn

        so = ort.SessionOptions()
        so.intra_op_num_threads = 1
        so.inter_op_num_threads = 1
        so.log_severity_level = 3
        self._sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])

        # tokens.txt：每行 "字 序号" 或 "字"，取首字段为字、行号为索引
        self._tokens = {}
        with open(tokens, encoding="utf-8") as f:
            for i, line in enumerate(f):
                self._tokens[i] = line.strip().split()[0] if line.strip() else ""
        self._tok_len = len(self._tokens)

        # CMVN（am.mvn）：取两段 <LearnRateCoef> 向量，第一段加、第二段乘
        self._cmvn_neg_mean, self._cmvn_inv_std = self._load_cmvn(mvn)
        self._fbank_opts = knf.FbankOptions()
        self._fbank_opts.frame_opts.dither = 0
        self._fbank_opts.frame_opts.snip_edges = False
        self._fbank_opts.frame_opts.samp_freq = 16000
        self._fbank_opts.mel_opts.num_bins = 80

    @staticmethod
    def _load_cmvn(path):
        neg_mean = None
        inv_std = None
        with open(path) as f:
            for line in f:
                if not line.startswith("<LearnRateCoef>"):
                    continue
                t = list(map(float, line.split()[3:-1]))
                if neg_mean is None:
                    neg_mean = np.array(t, dtype=np.float32)
                else:
                    inv_std = np.array(t, dtype=np.float32)
        if neg_mean is None or inv_std is None:
            # 退化：不做归一化
            neg_mean = np.zeros(80, dtype=np.float32)
            inv_std = np.ones(80, dtype=np.float32)
        return neg_mean, inv_std

    # ---- 特征 ----
    def _load_samples(self, wav_path):
        """读 wav -> (采样率, float32[-1,1])，必要时重采样到 16k。"""
        import soundfile as sf
        import scipy.signal as sig

        samples, rate = sf.read(wav_path, dtype="float32", always_2d=False)
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        if rate != 16000:
            g = int(16000 * samples.shape[0] / rate)
            samples = sig.resample_poly(samples, 16000, rate).astype(np.float32)
            rate = 16000
        return rate, samples

    def _extract_features(self, samples):
        """samples: float32[-1,1] @16k -> [T, 560] (fbank + LFR 窗)。"""
        import kaldi_native_fbank as knf

        opts = self._fbank_opts
        online = knf.OnlineFbank(opts)
        online.accept_waveform(16000, (samples * 32768).tolist())
        online.input_finished()
        feats = np.stack(
            [online.get_frame(i) for i in range(online.num_frames_ready)]
        ).astype(np.float32)

        # LFR: window=7, shift=6
        ws, wsh = 7, 6
        T = (feats.shape[0] - ws) // wsh + 1
        feats = np.lib.stride_tricks.as_strided(
            feats,
            shape=(T, feats.shape[1] * ws),
            strides=((wsh * feats.shape[1]) * 4, 4),
        )
        feats = (feats + self._cmvn_neg_mean) * self._cmvn_inv_std
        return feats

    # ---- 解码 ----
    @staticmethod
    def _is_special(tok: str) -> bool:
        return tok.startswith("<") and tok.endswith(">")

    def _decode(self, logits, token_num):
        """贪心解码 + BPE 子词合并（修复 §9.4 中英混合 @@ 连接符问题）。

        Paraformer-zh 的 BPE vocab 中英文以 ``@@`` 续接（如 ``ye@@``/``ster@@``/
        ``day`` -> ``yesterday``）；该模型无 ``▁`` 空格标记，故英文词间按 ASCII
        边界补空格，汉字之间不补。``<blank>``/``<s>``/``</s>``/``<unk>`` 等特殊
        token 跳过。
        """
        y = logits.argmax(axis=-1)[:token_num]
        words = []
        buf = ""
        for i in y:
            i = int(i)
            tok = self._tokens.get(i, "")
            if not tok or self._is_special(tok):
                continue
            if tok.endswith("@@"):
                buf += tok[:-2]
            else:
                buf += tok
                words.append(buf)
                buf = ""
        if buf:
            words.append(buf)

        if not words:
            return ""

        def _all_ascii(w: str) -> bool:
            return all(ord(c) < 128 for c in w)

        out = words[0]
        for prev, cur in zip(words, words[1:]):
            # 仅在两个 ASCII 词（英文）之间补空格；汉字/CJK 之间不补
            if _all_ascii(prev) and _all_ascii(cur):
                out += " " + cur
            else:
                out += cur
        return out

    # ---- 对外 ----
    def transcribe(self, wav_path: str) -> str:
        self.load()
        _, samples = self._load_samples(wav_path)
        feats = self._extract_features(samples)
        feats = feats.astype(np.float32)[np.newaxis, :, :]
        flen = np.array([feats.shape[1]], dtype=np.int32)
        # 按模型实际输出名取值（不同导出版本可能只含 logits+token_num，
        # 也可能额外含 us_alphas/us_cif_peak），动态匹配避免 InvalidArgument。
        out_names = [o.name for o in self._sess.get_outputs()]
        outs = self._sess.run(out_names, {"speech": feats, "speech_lengths": flen})
        out_map = dict(zip(out_names, outs))
        logits = out_map["logits"][0]
        token_num = int(out_map["token_num"][0])
        return self._decode(logits, token_num)
