#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大模型调用（OpenAI 兼容）与统一解析入口 process_text。"""
import json

from . import _state
from .demo import demo_process


def llm_process(dialect_text: str) -> dict:
    if not _state.LLM_READY:
        return demo_process(dialect_text)
    system_prompt = (
        "你是精通河南方言（中原官话）的语言学者。用户输入一句河南方言，"
        "请严格输出一个 JSON 对象，不要输出多余文字，格式如下：\n"
        '{"mandarin": "翻译成的普通话", "pinyin": "整句汉语拼音(带声调,词间空格)", '
        '"explanation": "用中文解释其中的生僻方言词含义、用法、来源；若不确定请如实说明"}\n'
        "要求：mandarin 用规范普通话；pinyin 仅含汉字拼音与空格；"
        "explanation 简明、有文化含量，并标注『释义由 AI 生成，仅供参考』。"
    )
    resp = _state.requests.post(
        _state.LLM_BASE_URL + "/chat/completions",
        headers={
            "Authorization": f"Bearer {_state.LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": _state.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": dialect_text},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        },
        timeout=40,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    try:
        data = json.loads(content)
    except Exception:
        data = {"mandarin": "", "pinyin": "", "explanation": content}
    data["dialect"] = dialect_text
    data["source"] = "llm"
    return data


def process_text(text: str) -> dict:
    """解析一句方言，返回标准化结果 dict。"""
    try:
        result = llm_process(text)
    except Exception as e:
        result = demo_process(text)
        result["source"] = "demo-fallback"
        result["note"] = "大模型调用失败，已用内置词库兜底：" + str(e)
    return result
