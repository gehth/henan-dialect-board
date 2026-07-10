# -*- coding: utf-8 -*-
"""自动更新检查（纯标准库，无第三方依赖，便于 offline / torch-free 包内运行）。

`check_for_update()` 拉取远端 `version.json` 清单，与本地 `__version__` 比较，
返回结构化结果。任何网络 / 解析错误都**优雅降级**（返回带 error 字段的 dict，不抛异常），
因此即使在无网环境调用也安全。

设计要点：
- 默认清单地址来自 `version.DEFAULT_MANIFEST_URL`（仓库根的 raw 地址，天然更新服务器）；
  可用 `manifest_url` 参数（来自设置项 `update_server_url`）或环境变量 `UPDATE_URL` 覆盖。
- 下载地址（portable / installer）由清单提供，未来挂 GitHub Release 即可用；
  客户端拿到 URL 后自行下载并可用 `sha256` 做完整性校验（本模块只负责「告知」，下载/安装由上层决定）。
"""
import json
import os
import urllib.request
import urllib.error

from version import __version__, compare_version, DEFAULT_MANIFEST_URL


def _resolve_url(manifest_url):
    if manifest_url:
        return manifest_url
    env = os.environ.get("UPDATE_URL")
    if env:
        return env
    return DEFAULT_MANIFEST_URL


def check_for_update(current_version=None, manifest_url=None, timeout=5):
    """检查是否有新版本。

    返回 dict：
      - 成功且需更新:
        {"update_available": True, "current", "latest", "summary", "changelog":[..],
         "release_date", "release_tag", "downloads":{..}, "min_version", "force": bool}
      - 已是最新:     {"update_available": False, "current", "latest"}
      - 出错(离线等): {"update_available": False, "error": "..."}
    """
    if current_version is None:
        current_version = __version__
    url = _resolve_url(manifest_url)
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "henan-dialect-board-updater"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            ValueError, OSError) as e:
        return {"update_available": False, "error": f"无法获取更新信息：{e}"}

    latest = data.get("version")
    if not latest:
        return {"update_available": False, "error": "更新清单缺少 version 字段"}

    update_available = compare_version(latest, current_version) > 0
    force = False
    min_v = data.get("min_version")
    if min_v and compare_version(current_version, min_v) < 0:
        # 低于最低支持版本：强制提示更新
        force = True
        update_available = True

    return {
        "update_available": update_available,
        "current": current_version,
        "latest": latest,
        "summary": data.get("summary", ""),
        "changelog": data.get("changelog", []),
        "release_date": data.get("release_date", ""),
        "release_tag": data.get("release_tag", ""),
        "downloads": data.get("downloads", {}),
        "min_version": min_v,
        "force": force,
    }
