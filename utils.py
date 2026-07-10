#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公共工具函数：供各模块复用，避免重复样板与逻辑散落。

包含：
- run_worker：创建并启动后台 Worker，自动在完成后释放（替代每处 4 行样板）
- mode_text：根据 backend.get_status() 返回生成导航栏识别方式文字（单一来源）
"""
from worker import Worker


def run_worker(fn, *args, on_finished, on_error):
    """创建并启动后台 Worker，完成时自动 deleteLater；返回 Worker 实例（调用方可自行持有）。

    on_finished / on_error 为槽函数或 lambda。集中处理「finished/error → 业务槽 + deleteLater」
    的重复连接，调用处只需一行。
    """
    w = Worker(fn, *args)
    w.finished.connect(on_finished)
    w.error.connect(on_error)
    w.finished.connect(w.deleteLater)
    w.error.connect(w.deleteLater)
    w.start()
    return w


def mode_text(status: dict) -> str:
    """根据 backend.get_status() 的返回生成导航栏识别方式文字（单一来源）。"""
    if status.get("demo"):
        return "● 演示模式（内置词库）"
    if status.get("offline_onnx"):
        return "● 离线识别（本地 FunASR-ONNX）"
    if status.get("offline_asr"):
        return "● 离线识别（FunASR torch）"
    return "● 云端模式"
