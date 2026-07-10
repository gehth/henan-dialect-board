#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用后台工作线程：在子线程执行耗时函数，结果通过信号回传主线程。"""
from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
