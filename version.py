# -*- coding: utf-8 -*-
"""应用版本单一来源 + 版本比较工具。

- `__version__` 是全局唯一版本号（打包 spec / 安装脚本 / 关于对话框 / 更新检查都读它）。
- `DEFAULT_MANIFEST_URL` 指向仓库根 `version.json` 的 raw 地址，
  GitHub raw 即天然的「更新服务器」，无需自建后端；可用设置项 / 环境变量覆盖。
"""
import re

__version__ = "2.0.0"

APP_NAME = "河南方言语音板"
REPO_URL = "https://github.com/gehth/henan-dialect-board"

# 更新清单默认地址（放在仓库根，raw.githubusercontent 即天然更新服务器；可用设置/环境变量覆盖）
DEFAULT_MANIFEST_URL = "https://raw.githubusercontent.com/gehth/henan-dialect-board/main/version.json"


def parse_version(v):
    """'2.0.0' -> (2, 0, 0)；取每段前导数字（'v2.0.0rc1' -> (2,0,0)），
    非数字段按 0 处理；自动补齐到 3 段。"""
    parts = []
    for p in str(v).split("."):
        m = re.search(r"\d+", p)
        parts.append(int(m.group()) if m else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def compare_version(a, b):
    """a < b -> -1，a == b -> 0，a > b -> 1。"""
    pa, pb = parse_version(a), parse_version(b)
    return (pa > pb) - (pa < pb)
