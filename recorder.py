#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦克风录音（桌面版，替代原浏览器的 getUserMedia）。
- 使用 sounddevice 录音（16k / 单声道 / int16）
- 回调中实时计算 RMS 电平，供 UI 音量条轮询
- stop() 返回标准 WAV 字节
"""
import io
import wave
import threading

import numpy as np
import sounddevice as sd


class Recorder:
    def __init__(self, rate: int = 16000, channels: int = 1):
        self.rate = rate
        self.channels = channels
        self._frames = []
        self._stream = None
        self._recording = False
        self._level = 0.0
        self._lock = threading.Lock()
        self._error = None

    @staticmethod
    def list_input_devices():
        try:
            devs = sd.query_devices()
            return [(i, d["name"]) for i, d in enumerate(devs) if d.get("max_input_channels", 0) > 0]
        except Exception:
            return []

    @property
    def is_recording(self):
        return self._recording

    def start(self):
        if self._recording:
            return
        if not self.list_input_devices():
            raise RuntimeError("未检测到麦克风输入设备")
        self._frames = []
        self._level = 0.0
        self._error = None

        def callback(indata, frames, time_info, status):
            if status:
                pass
            data = indata.copy()
            with self._lock:
                self._frames.append(data)
            rms = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))
            # int16 满幅 ~32768，按经验缩放成 0~1 的电平
            lvl = min(1.0, rms / 5000.0)
            self._level = max(self._level * 0.6, lvl)  # 加一点平滑

        self._stream = sd.InputStream(
            samplerate=self.rate,
            channels=self.channels,
            dtype="int16",
            blocksize=2048,
            callback=callback,
        )
        self._stream.start()
        self._recording = True

    def stop(self):
        """停止录音，返回 WAV 字节；未录到内容返回 None。"""
        if not self._recording:
            return None
        self._recording = False
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception:
            pass
        self._stream = None
        with self._lock:
            frames = self._frames
            self._frames = []
        if not frames:
            return None
        audio = np.concatenate(frames, axis=0)
        return self._to_wav_bytes(audio)

    def get_level(self):
        """返回 0~1 的实时音量电平。"""
        return self._level

    def _to_wav_bytes(self, audio_int16):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(self.channels)
            w.setsampwidth(2)
            w.setframerate(self.rate)
            w.writeframes(audio_int16.tobytes())
        return buf.getvalue()
