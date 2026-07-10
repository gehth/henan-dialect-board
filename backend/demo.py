#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""演示 / 兜底引擎：无 LLM 时用内置词库做方言->普通话解析（带 LRU 缓存）。"""
import copy
import functools

from . import _state
from .pinyin import pinyin_of


def _demo_process_impl(dialect_text: str) -> dict:
    text = (dialect_text or "").strip()
    if not text:
        return {"dialect": "", "mandarin": "", "pinyin": "", "explanation": "", "source": "demo", "word_pinyin": ""}
    mandarin_parts = []
    expls = []
    word_py = []
    i = 0
    n = len(text)
    while i < n:
        matched = None
        for ph in _state._DICT_INDEX.get(text[i], []):
            w = ph["dialect"]
            if text.startswith(w, i):
                matched = ph
                break
        if matched:
            mandarin_parts.append(matched["mandarin"].split(" / ")[0])
            expls.append(f"【{matched['dialect']}】{matched['explanation']}")
            py = matched.get("pinyin") or pinyin_of(matched["dialect"])
            word_py.append(f"{matched['dialect']}[{py}]")
            i += len(matched["dialect"])
        else:
            mandarin_parts.append(text[i])
            i += 1
    mandarin = "".join(mandarin_parts)
    pinyin_txt = pinyin_of(mandarin) or pinyin_of(text)
    if expls:
        explanation = "；".join(expls)
    else:
        explanation = "（词库暂无该句释义，可接入大模型获得更准确的解释）"
    return {
        "dialect": text,
        "mandarin": mandarin,
        "pinyin": pinyin_txt,
        "explanation": explanation,
        "source": "demo",
        "word_pinyin": "  ".join(word_py),
    }


@functools.lru_cache(maxsize=512)
def _demo_process_cached(text):
    """demo_process 的内部实现，带 LRU 缓存（按文本去重计算结果）。"""
    return _demo_process_impl(text)


def demo_process(dialect_text: str) -> dict:
    """解析一句方言（演示/兜底）。结果带 LRU 内存缓存，返回深拷贝副本避免调用方修改污染缓存。"""
    return copy.deepcopy(_demo_process_cached(dialect_text))
