#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backend 纯逻辑测试：纠错 / 演示解析 / 词库聚合（不依赖 PySide6、网络、onnxruntime）。

运行：python -m unittest tests.test_backend -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 让测试从项目根目录运行时能 import backend / store
import backend
from backend import correct_text, demo_process, get_dict, get_dict_packages, get_examples


class TestCorrect(unittest.TestCase):
    def test_empty_short(self):
        self.assertEqual(correct_text(""), {"text": "", "suggestion": ""})
        self.assertEqual(correct_text("中"), {"text": "中", "suggestion": ""})

    def test_exact_dict_word_no_suggestion(self):
        phrases = get_dict()["phrases"]
        self.assertTrue(len(phrases) > 0)
        w = phrases[0]["dialect"]
        self.assertEqual(correct_text(w)["suggestion"], "")

    def test_unknown_no_false_positive(self):
        # 明显不在词库中的长字符串不应给出误纠正
        out = correct_text("今天天气真不错我们去公园玩吧")
        self.assertIn("text", out)
        self.assertIn("suggestion", out)


class TestDemoProcess(unittest.TestCase):
    def test_keys(self):
        r = demo_process("中")
        for k in ("dialect", "mandarin", "pinyin", "explanation", "source", "word_pinyin"):
            self.assertIn(k, r)
        self.assertEqual(r["source"], "demo")

    def test_known_dialect_translates(self):
        phrases = get_dict()["phrases"]
        w = phrases[0]["dialect"]
        r = demo_process(w)
        self.assertEqual(r["dialect"], w)
        self.assertTrue(r["mandarin"])  # 应能得到普通话释义


class TestDictionary(unittest.TestCase):
    def test_aggregate_over_1000(self):
        d = get_dict()
        self.assertGreaterEqual(len(d["phrases"]), 1000)

    def test_packages_loaded(self):
        pkgs = get_dict_packages()
        self.assertTrue(any(p["file"] == "dialect_dict.json" for p in pkgs))

    def test_examples_shape(self):
        ex = get_examples()
        self.assertIsInstance(ex, list)
        self.assertIn("dialect", ex[0])
        self.assertIn("mandarin", ex[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
