#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拼音计算：整串一次性调用 pypinyin（内部批量分词），远快于逐字符调用。"""
from ._state import pinyin, Style


def pinyin_of(text: str) -> str:
    """整串一次性调用 pypinyin（内部批量分词处理），远快于逐字符调用。"""
    if not text or pinyin is None:
        return ""
    try:
        syls = pinyin(text, style=Style.TONE, heteronym=False)
        parts = []
        for syl in syls:
            s = syl[0] if syl else ""
            # 仅保留含字母的拼音音节，过滤标点/数字/空格
            if any(c.isalpha() for c in s):
                parts.append(s)
        return " ".join(parts)
    except Exception:
        return ""
