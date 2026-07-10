# -*- coding: utf-8 -*-
"""自动更新检查模块的单测（离线，用本地 file:// 清单，不依赖网络）。"""
import json
import os
import tempfile
import unittest

from version import parse_version, compare_version
from backend.update_check import check_for_update


class VersionCompareTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_version("2.0.0"), (2, 0, 0))
        self.assertEqual(parse_version("2.1"), (2, 1, 0))
        self.assertEqual(parse_version("v2.0.0rc1"), (2, 0, 0))

    def test_compare(self):
        self.assertEqual(compare_version("2.0.0", "2.0.0"), 0)
        self.assertEqual(compare_version("2.1.0", "2.0.0"), 1)
        self.assertEqual(compare_version("1.9.9", "2.0.0"), -1)


class UpdateCheckTest(unittest.TestCase):
    def _write(self, d):
        fd, path = tempfile.mkstemp(suffix=".json", prefix="ver_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        return "file:///" + path.replace("\\", "/")

    def test_newer_available(self):
        url = self._write({"version": "2.1.0", "summary": "新版本",
                           "changelog": ["改动A"], "downloads": {}})
        r = check_for_update("2.0.0", url)
        self.assertTrue(r["update_available"])
        self.assertEqual(r["latest"], "2.1.0")
        self.assertEqual(r["changelog"], ["改动A"])

    def test_already_latest(self):
        url = self._write({"version": "2.0.0"})
        r = check_for_update("2.0.0", url)
        self.assertFalse(r["update_available"])
        self.assertEqual(r["current"], "2.0.0")

    def test_force_below_min(self):
        url = self._write({"version": "2.1.0", "min_version": "2.5.0"})
        r = check_for_update("2.0.0", url)
        self.assertTrue(r["update_available"])
        self.assertTrue(r["force"])

    def test_offline_error(self):
        r = check_for_update("2.0.0", "file:///nonexistent_path_xyz/version.json")
        self.assertFalse(r["update_available"])
        self.assertIn("error", r)


if __name__ == "__main__":
    unittest.main()
