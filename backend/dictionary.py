#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""方言词库：多包聚合加载、索引重建、用户自定义词库 CRUD、数据查询接口。"""
import os
import glob
import json

from . import _state
from .pinyin import pinyin_of


# 内置词库：支持多包聚合（dialect_dict*.json，除 .bak），按文件名排序主包在前
def _load_dict_packages():
    """聚合所有 dialect_dict*.json 词库包，去重（按 dialect 字段），主包 meta 优先。"""
    d = os.path.dirname(_state.resource_path("dialect_dict.json"))
    paths = sorted(glob.glob(os.path.join(d, "dialect_dict*.json")))
    # 主包（dialect_dict.json）meta/词条优先：确保它排在所有扩展包之前
    paths.sort(key=lambda p: 0 if os.path.basename(p) == "dialect_dict.json" else 1)
    # 用户自定义词库（exe 同目录，可写持久化）也加入聚合
    up = _state._user_dict_path()
    if os.path.exists(up):
        paths.append(up)
    phrases, cities, meta, packages = [], [], {}, []
    seen = set()
    for p in paths:
        if p.endswith(".bak"):
            continue
        try:
            data = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        pkg = os.path.basename(p)
        added = 0
        for ph in data.get("phrases", []):
            key = ph.get("dialect", "")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            phrases.append(ph)
            added += 1
        cities.extend(data.get("cities", []))
        if not meta and data.get("meta"):
            meta = data["meta"]  # 主包（排序第一）meta 优先
        packages.append({"file": pkg, "count": added})
    return phrases, cities, meta, packages


def _rebuild_index():
    """补全缺失拼音 + 重建首字索引/集合/分桶（加载与热更新共用）。"""
    for _p in _state.DICT_PHRASES:
        if not _p.get("pinyin"):
            _p["pinyin"] = pinyin_of(_p.get("dialect", ""))
    _state._DICT_SORTED = sorted(_state.DICT_PHRASES, key=lambda x: len(x["dialect"]), reverse=True)
    _state._DICT_INDEX = {}
    for _p in _state._DICT_SORTED:
        _d = _p.get("dialect", "")
        if _d:
            _state._DICT_INDEX.setdefault(_d[0], []).append(_p)
    _state._DIALECT_SET = set(p.get("dialect", "") for p in _state.DICT_PHRASES)
    _state._BY_LEN = {}
    for p in _state.DICT_PHRASES:
        _l = len(p.get("dialect", ""))
        _state._BY_LEN.setdefault(_l, []).append(p.get("dialect", ""))


def _reload_dict():
    """重新加载所有词库包并重建索引（用户增删词后调用）。"""
    _state.DICT_PHRASES, _state.DICT_CITIES, _state.DICT_META, _state.DICT_PACKAGES = _load_dict_packages()
    _state.DICT = {"meta": _state.DICT_META, "phrases": _state.DICT_PHRASES,
                   "cities": _state.DICT_CITIES}
    _rebuild_index()


def _read_user_dict() -> dict:
    up = _state._user_dict_path()
    if os.path.exists(up):
        try:
            return json.load(open(up, encoding="utf-8"))
        except Exception:
            pass
    return {"meta": {"name": "用户自定义词库", "version": "1.0", "count": 0}, "phrases": []}


def _write_user_dict(data: dict):
    up = _state._user_dict_path()
    os.makedirs(os.path.dirname(up) or ".", exist_ok=True)
    json.dump(data, open(up, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def add_custom_word(dialect, mandarin, category="自定义", pinyin="",
                    explanation="", region="通用") -> bool:
    """新增/更新一条用户自定义方言词（写入 user_dict.json 并热重载）。"""
    dialect = (dialect or "").strip()
    mandarin = (mandarin or "").strip()
    if not dialect or not mandarin:
        raise ValueError("方言词与普通话释义均不能为空")
    data = _read_user_dict()
    phs = data.setdefault("phrases", [])
    for p in phs:
        if p.get("dialect") == dialect:
            p.update(mandarin=mandarin, category=category or "自定义",
                     region=region or "通用",
                     explanation=explanation or p.get("explanation", ""),
                     pinyin=pinyin or p.get("pinyin", ""))
            break
    else:
        phs.append({"dialect": dialect, "mandarin": mandarin,
                    "category": category or "自定义", "region": region or "通用",
                    "pinyin": pinyin, "explanation": explanation})
    data.setdefault("meta", {})["count"] = len(phs)
    _write_user_dict(data)
    _reload_dict()
    return True


def remove_custom_word(dialect: str) -> bool:
    """删除一条用户自定义方言词。"""
    dialect = (dialect or "").strip()
    if not dialect:
        return False
    data = _read_user_dict()
    phs = data.get("phrases", [])
    new = [p for p in phs if p.get("dialect") != dialect]
    if len(new) == len(phs):
        return False
    data["phrases"] = new
    data.setdefault("meta", {})["count"] = len(new)
    _write_user_dict(data)
    _reload_dict()
    return True


def import_custom_dict(path: str) -> int:
    """从 JSON 导入自定义词条（支持 {phrases:[...]} 或 [...]）。返回导入条数。"""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict):
        items = raw.get("phrases", [])
    elif isinstance(raw, list):
        items = raw
    else:
        items = []
    data = _read_user_dict()
    phs = data.setdefault("phrases", [])
    n = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        d = (it.get("dialect") or "").strip()
        m = (it.get("mandarin") or "").strip()
        if not d or not m:
            continue
        for p in phs:
            if p.get("dialect") == d:
                p.update(mandarin=m, category=it.get("category", p.get("category", "自定义")),
                         region=it.get("region", p.get("region", "通用")),
                         explanation=it.get("explanation", p.get("explanation", "")),
                         pinyin=it.get("pinyin", p.get("pinyin", "")))
                break
        else:
            phs.append({"dialect": d, "mandarin": m,
                        "category": it.get("category", "自定义"),
                        "region": it.get("region", "通用"),
                        "pinyin": it.get("pinyin", ""),
                        "explanation": it.get("explanation", "")})
        n += 1
    data.setdefault("meta", {})["count"] = len(phs)
    _write_user_dict(data)
    _reload_dict()
    return n


# ============================ 数据接口 ============================
def get_dict() -> dict:
    return {"meta": _state.DICT.get("meta", {}), "phrases": _state.DICT_PHRASES,
            "cities": _state.DICT_CITIES, "packages": _state.DICT_PACKAGES}


def get_dict_packages() -> list:
    """返回已加载的词库包清单（多包聚合信息）。"""
    return _state.DICT_PACKAGES


def get_examples() -> list:
    return [{"dialect": p["dialect"], "mandarin": p["mandarin"]} for p in _state.DICT_PHRASES]


def get_user_words() -> list:
    """返回当前用户自定义词条列表。"""
    return _read_user_dict().get("phrases", [])


# 导入时即加载词库并构建索引（与原始 backend.py 顶层行为一致）
_state.DICT_PHRASES, _state.DICT_CITIES, _state.DICT_META, _state.DICT_PACKAGES = _load_dict_packages()
_state.DICT = {"meta": _state.DICT_META, "phrases": _state.DICT_PHRASES,
               "cities": _state.DICT_CITIES}
_rebuild_index()
