#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""store.py 数据层测试：覆盖增删改查、去重、上限、设置读写与旧 JSON 迁移。

运行：python -m unittest tests.test_store -v
"""
import os
import sys
import json
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import store


def _tmp_data_dir():
    d = tempfile.mkdtemp(prefix="henan_store_test_")
    store._DATA_DIR = d
    store._DATA_FILE = os.path.join(d, "user_data.json")
    store._DB_FILE = os.path.join(d, "user_data.db")
    store._reset()
    return d


_SAMPLE = {
    "dialect": "信球",
    "mandarin": "傻、笨",
    "pinyin": "xìn qiú",
    "word_pinyin": "信球[xìn qiú]",
    "explanation": "形容人傻、脑子不灵光",
    "source": "demo",
}


class StoreBase(unittest.TestCase):
    def setUp(self):
        self._dir = _tmp_data_dir()

    def tearDown(self):
        store._reset()
        shutil.rmtree(self._dir, ignore_errors=True)


class TestHistory(StoreBase):
    def test_add_and_get(self):
        store.add_history(_SAMPLE)
        hist = store.get_history()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["dialect"], "信球")

    def test_dedup_by_dialect(self):
        store.add_history(_SAMPLE)
        store.add_history(dict(_SAMPLE, mandarin="笨蛋（覆盖）"))
        hist = store.get_history()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["mandarin"], "笨蛋（覆盖）")

    def test_cap_50(self):
        for i in range(60):
            store.add_history({"dialect": f"词{i:02d}", "mandarin": str(i)})
        self.assertEqual(len(store.get_history()), 50)
        # 最新在前：应为最后写入的 词59..词10
        self.assertEqual(store.get_history()[0]["dialect"], "词59")

    def test_remove_and_clear(self):
        store.add_history(_SAMPLE)
        rid = store.get_history()[0]["id"]
        store.remove_history(rid)
        self.assertEqual(store.get_history(), [])
        store.add_history(_SAMPLE)
        store.clear_history()
        self.assertEqual(store.get_history(), [])


class TestFavorites(StoreBase):
    def test_add_is_favorite_remove(self):
        self.assertFalse(store.is_favorite("信球"))
        store.add_favorite(_SAMPLE)
        self.assertTrue(store.is_favorite("信球"))
        store.add_favorite(_SAMPLE)  # 重复添加应去重
        self.assertEqual(len(store.get_favorites()), 1)
        store.remove_favorite("信球")
        self.assertFalse(store.is_favorite("信球"))

    def test_clear_favorites(self):
        store.add_favorite(_SAMPLE)
        store.clear_favorites()
        self.assertEqual(store.get_favorites(), [])


class TestWrongWords(StoreBase):
    def test_add_dedup_remove_clear(self):
        store.add_wrong_word(_SAMPLE)
        store.add_wrong_word(_SAMPLE)
        self.assertEqual(len(store.get_wrong_words()), 1)
        store.remove_wrong_word("信球")
        self.assertEqual(store.get_wrong_words(), [])
        store.add_wrong_word(_SAMPLE)
        store.clear_wrong_words()
        self.assertEqual(store.get_wrong_words(), [])


class TestSettings(StoreBase):
    def test_defaults(self):
        s = store.get_settings()
        self.assertEqual(s["theme"], "dark")
        self.assertEqual(s["font_scale"], 1.0)

    def test_roundtrip(self):
        store.set_setting("theme", "light")
        self.assertEqual(store.get_setting("theme"), "light")
        # 类型保持：float / bool
        store.set_setting("font_scale", 1.25)
        self.assertEqual(store.get_setting("font_scale"), 1.25)
        store.set_setting("minimize_to_tray", True)
        self.assertIs(store.get_setting("minimize_to_tray"), True)
        # 默认值补齐
        self.assertIn("tts_voice", store.get_settings())

    def test_missing_returns_default(self):
        self.assertEqual(store.get_setting("nope", "fallback"), "fallback")
        self.assertIsNone(store.get_setting("nope"))


class TestLegacyMigration(StoreBase):
    def test_json_migrated_once(self):
        legacy = {
            "history": [dict(_SAMPLE, ts="2026-01-01 00:00:00")],
            "favorites": [dict(_SAMPLE, dialect="中", mandarin="对")],
            "wrong_words": [dict(_SAMPLE, dialect="恁", mandarin="你")],
            "settings": {"theme": "light", "font_scale": 2.0},
        }
        with open(store._DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(legacy, f, ensure_ascii=False)
        # 触发连接建立 + 迁移
        self.assertEqual(len(store.get_history()), 1)
        self.assertEqual(len(store.get_favorites()), 1)
        self.assertEqual(len(store.get_wrong_words()), 1)
        self.assertEqual(store.get_setting("theme"), "light")
        self.assertEqual(store.get_setting("font_scale"), 2.0)
        # 旧文件应被改名 .migrated，避免二次迁移
        self.assertTrue(os.path.exists(store._DATA_FILE + ".migrated"))
        self.assertFalse(os.path.exists(store._DATA_FILE))
        # 二次触发不应重复导入
        self.assertEqual(len(store.get_history()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
