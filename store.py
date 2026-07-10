#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地存储：历史记录（解析成功自动写入）、收藏（手动）、错词本（学习互动）与设置项
的 SQLite 持久化。

数据层（2026-07-09 升级）：
- 原 user_data.json（整文件读写）升级为 SQLite（~/.henan_dialect/user_data.db），
  支持并发安全写入、单条增删、按需查询，避免每次操作全量序列化大 JSON；
- 首次启动时若发现旧的 user_data.json，自动迁移到 SQLite（迁移后原文件改名 .migrated）；
- 公共 API 完全兼容旧 JSON 版本，调用方（main.py / page_*.py）无需改动。
"""
import os
import json
import time
import uuid
import threading
import sqlite3

_DATA_DIR = os.path.join(os.path.expanduser("~"), ".henan_dialect")
_DATA_FILE = os.path.join(_DATA_DIR, "user_data.json")   # 旧版 JSON（迁移来源）
_DB_FILE = os.path.join(_DATA_DIR, "user_data.db")        # 新版 SQLite
_MAX_HISTORY = 50

# 设置项默认值（主题 / 字号缩放 / 识别引擎 / TTS 音色 / 最小化到托盘）
_DEFAULT_SETTINGS = {
    "theme": "dark",
    "font_scale": 1.0,
    "asr_engine": "auto",
    "tts_voice": "mandarin",
    "minimize_to_tray": False,
}

_lock = threading.Lock()
_conn = None  # 懒加载的 sqlite 连接（check_same_thread=False + 全局锁保证串行访问）


def _get_conn():
    """返回（必要时创建）SQLite 连接，并确保表结构与旧数据迁移就位。"""
    global _conn
    if _conn is None:
        os.makedirs(_DATA_DIR, exist_ok=True)
        _conn = sqlite3.connect(_DB_FILE, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _init_schema(_conn)
        _migrate_legacy(_conn)
    return _conn


def _init_schema(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS records(
            seq         INTEGER PRIMARY KEY AUTOINCREMENT,
            kind        TEXT NOT NULL,            -- history | favorites | wrong_words
            id          TEXT,
            ts          TEXT,
            dialect     TEXT,
            mandarin    TEXT,
            pinyin      TEXT,
            word_pinyin TEXT,
            explanation TEXT,
            source      TEXT
        )"""
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)"
    )
    conn.commit()


def _migrate_legacy(conn):
    """把旧版 user_data.json 一次性导入 SQLite（仅当 records 表为空且旧文件存在）。"""
    if not os.path.exists(_DATA_FILE):
        return
    try:
        with open(_DATA_FILE, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            d = {}
    except Exception:
        d = {}
    cur = conn.execute("SELECT COUNT(*) FROM records")
    if cur.fetchone()[0] == 0:
        for kind in ("history", "favorites", "wrong_words"):
            for rec in d.get(kind, []) or []:
                if isinstance(rec, dict):
                    _insert_record(conn, kind, rec)
        for k, v in (d.get("settings", {}) or {}).items():
            conn.execute(
                "INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)",
                (k, json.dumps(v, ensure_ascii=False)),
            )
        conn.commit()
    # 迁移完成后改名，避免重复迁移
    try:
        os.replace(_DATA_FILE, _DATA_FILE + ".migrated")
    except Exception:
        pass


def _reset():
    """测试辅助：关闭连接并置空，使下次调用按当前 _DB_FILE 重新打开（含迁移）。"""
    global _conn
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = None


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _norm(record):
    return {
        "id": record.get("id") or uuid.uuid4().hex[:10],
        "ts": record.get("ts") or _now(),
        "dialect": record.get("dialect", ""),
        "mandarin": record.get("mandarin", ""),
        "pinyin": record.get("pinyin", ""),
        "word_pinyin": record.get("word_pinyin", ""),
        "explanation": record.get("explanation", ""),
        "source": record.get("source", ""),
    }


def _insert_record(conn, kind, record):
    r = _norm(record)
    conn.execute(
        """INSERT INTO records(kind, id, ts, dialect, mandarin, pinyin, word_pinyin, explanation, source)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (kind, r["id"], r["ts"], r["dialect"], r["mandarin"], r["pinyin"],
         r["word_pinyin"], r["explanation"], r["source"]),
    )


def _rows_to_list(conn, kind):
    cur = conn.execute(
        """SELECT id, ts, dialect, mandarin, pinyin, word_pinyin, explanation, source
           FROM records WHERE kind=? ORDER BY seq DESC""",
        (kind,),
    )
    return [
        {
            "id": row[0], "ts": row[1], "dialect": row[2], "mandarin": row[3],
            "pinyin": row[4], "word_pinyin": row[5], "explanation": row[6],
            "source": row[7],
        }
        for row in cur.fetchall()
    ]


# ----------------------------- 历史记录 -----------------------------
def add_history(result: dict):
    """解析成功时调用，自动写入历史（按方言去重，最多 50 条，最新在前）。"""
    if not result or not result.get("dialect"):
        return
    with _lock:
        conn = _get_conn()
        conn.execute(
            "DELETE FROM records WHERE kind='history' AND dialect=?",
            (result.get("dialect"),),
        )
        _insert_record(conn, "history", result)
        # 仅保留最新的 _MAX_HISTORY 条
        conn.execute(
            """DELETE FROM records
               WHERE kind='history'
                 AND seq NOT IN (
                     SELECT seq FROM records WHERE kind='history'
                     ORDER BY seq DESC LIMIT ?
                 )""",
            (_MAX_HISTORY,),
        )
        conn.commit()


def remove_history(item_id: str):
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM records WHERE kind='history' AND id=?", (item_id,))
        conn.commit()


def clear_history():
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM records WHERE kind='history'")
        conn.commit()


def get_history() -> list:
    with _lock:
        return _rows_to_list(_get_conn(), "history")


# ----------------------------- 收藏 -----------------------------
def add_favorite(result: dict):
    if not result or not result.get("dialect"):
        return
    with _lock:
        conn = _get_conn()
        conn.execute(
            "DELETE FROM records WHERE kind='favorites' AND dialect=?",
            (result.get("dialect"),),
        )
        _insert_record(conn, "favorites", result)
        conn.commit()


def remove_favorite(dialect: str):
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM records WHERE kind='favorites' AND dialect=?", (dialect,))
        conn.commit()


def is_favorite(dialect: str) -> bool:
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "SELECT 1 FROM records WHERE kind='favorites' AND dialect=? LIMIT 1",
            (dialect,),
        )
        return cur.fetchone() is not None


def clear_favorites():
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM records WHERE kind='favorites'")
        conn.commit()


def get_favorites() -> list:
    with _lock:
        return _rows_to_list(_get_conn(), "favorites")


# ----------------------------- 错词本（学习互动） -----------------------------
def add_wrong_word(record: dict):
    """猜方言答错时记录，便于「错词本」重点复习。按方言去重，最新在前。"""
    if not record or not record.get("dialect"):
        return
    with _lock:
        conn = _get_conn()
        conn.execute(
            "DELETE FROM records WHERE kind='wrong_words' AND dialect=?",
            (record.get("dialect"),),
        )
        _insert_record(conn, "wrong_words", record)
        conn.commit()


def remove_wrong_word(dialect: str):
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM records WHERE kind='wrong_words' AND dialect=?", (dialect,))
        conn.commit()


def clear_wrong_words():
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM records WHERE kind='wrong_words'")
        conn.commit()


def get_wrong_words() -> list:
    with _lock:
        return _rows_to_list(_get_conn(), "wrong_words")


# ----------------------------- 设置项 -----------------------------
def get_setting(key: str, default=None):
    """读取设置项；未设置时返回默认值（未提供 default 且不在默认表里则返 None）。"""
    with _lock:
        cur = _get_conn().execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
    if row is not None:
        try:
            return json.loads(row[0])
        except Exception:
            return row[0]
    if default is not None:
        return default
    return _DEFAULT_SETTINGS.get(key)


def set_setting(key: str, value):
    """写入单个设置项并落盘。"""
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        conn.commit()


def get_settings() -> dict:
    """返回设置项副本（含默认值补齐）。"""
    with _lock:
        cur = _get_conn().execute("SELECT key, value FROM settings")
        stored = {}
        for k, v in cur.fetchall():
            try:
                stored[k] = json.loads(v)
            except Exception:
                stored[k] = v
    s = dict(_DEFAULT_SETTINGS)
    s.update(stored)
    return s
