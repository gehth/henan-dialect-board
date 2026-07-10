#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大模型配置（GUI 设置面板用）：读取 / 运行时更新 / 持久化到 .env。"""
import os

from . import _state


def get_llm_config() -> dict:
    """返回当前大模型配置（供设置面板初始化显示）。"""
    return {
        "llm_api_key": _state.LLM_API_KEY,
        "llm_base_url": _state.LLM_BASE_URL,
        "llm_model": _state.LLM_MODEL,
    }


def set_llm_config(api_key: str, base_url: str, model: str):
    """运行时更新大模型配置，立即可用：写 os.environ + 共享状态，并重算 LLM_READY / DEMO_MODE。"""
    _state.LLM_API_KEY = (api_key or "").strip()
    _state.LLM_BASE_URL = (base_url or "https://api.deepseek.com").strip().rstrip("/")
    _state.LLM_MODEL = (model or "deepseek-chat").strip()
    os.environ["LLM_API_KEY"] = _state.LLM_API_KEY
    os.environ["LLM_BASE_URL"] = _state.LLM_BASE_URL
    os.environ["LLM_MODEL"] = _state.LLM_MODEL
    _state.LLM_READY = bool(_state.LLM_API_KEY)
    _state.DEMO_MODE = not (_state.ASR_READY and _state.LLM_READY)


def save_llm_config_to_env(api_key: str, base_url: str, model: str):
    """把大模型三项写回 exe 同目录的 .env（保留其他配置行）。下次启动 load_dotenv 自动读取。"""
    api_key = (api_key or "").strip()
    base_url = (base_url or "https://api.deepseek.com").strip().rstrip("/")
    model = (model or "deepseek-chat").strip()
    try:
        kept = []
        if os.path.exists(_state._env_path):
            with open(_state._env_path, encoding="utf-8") as f:
                for ln in f.read().splitlines():
                    s = ln.strip()
                    if s.startswith("LLM_API_KEY=") or s.startswith("LLM_BASE_URL=") or s.startswith("LLM_MODEL="):
                        continue
                    kept.append(ln)
        body = "\n".join(kept).rstrip("\n")
        block = "\n".join([
            f"LLM_API_KEY={api_key}",
            f"LLM_BASE_URL={base_url}",
            f"LLM_MODEL={model}",
        ])
        with open(_state._env_path, "w", encoding="utf-8") as f:
            f.write((body + "\n" if body else "") + block + "\n")
    except Exception:
        pass
