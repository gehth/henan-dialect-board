#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""识别智能纠错：基于内置词库的轻量编辑距离建议。"""
from . import _state


def _lev(a: str, b: str) -> int:
    """Levenshtein 编辑距离（短字符串够用）。"""
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[lb]


def correct_text(raw: str) -> dict:
    """
    基于内置词库的轻量纠错：识别（或输入）结果与某方言词条
    仅差 1 个字（同音/近形/多漏一字）时，给出修正建议。
    """
    raw = (raw or "").strip()
    if not raw or len(raw) < 2:
        return {"text": raw, "suggestion": ""}
    # 原文本身已是词库词条，无需纠错（O(1) 集合命中）
    if raw in _state._DIALECT_SET:
        return {"text": raw, "suggestion": ""}
    L = len(raw)
    # 第一优先：长度相同、恰好错 1 字（最可能同音/近形错字）
    for c in _state._BY_LEN.get(L, []):
        if _lev(raw, c) == 1:
            return {"text": raw, "suggestion": c}
    # 第二优先：长度差 1、编辑距离 1（识别多/少一字）
    for d in (L - 1, L + 1):
        for c in _state._BY_LEN.get(d, []):
            if _lev(raw, c) == 1:
                return {"text": raw, "suggestion": c}
    return {"text": raw, "suggestion": ""}
