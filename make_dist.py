# -*- coding: utf-8 -*-
"""生成可分发的 zip 包：把最新一次构建目录（对外统一命名为 河南方言语音板/）+ 文档 + .env.example 压成一个文件。

构建输出目录约定：dist/河南方言语音板_build/ 或 dist/河南方言语音板_b<时间戳>/。
每次打使用全新时间戳目录可避开 Defender/索引服务持锁导致的「清空旧目录失败」，
本脚本自动选取 dist/ 下最新、可读的构建目录作为打包源。
"""
import os, zipfile, datetime, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_ROOT = os.path.join(ROOT, "dist")

# 自动选取 dist/ 下最新的「河南方言语音板_b*」构建目录（含 _build 与 _b时间戳 两类）
candidates = []
for p in glob.glob(os.path.join(DIST_ROOT, "河南方言语音板_b*")):
    if os.path.isdir(p) and os.access(p, os.R_OK):
        try:
            # 以目录内 exe 是否存在判断是否为有效构建，并以 mtime 取最新
            if os.path.exists(os.path.join(p, "河南方言语音板.exe")):
                candidates.append((os.path.getmtime(p), p))
        except OSError:
            continue
if not candidates:
    raise SystemExit("未在 dist/ 下找到有效的构建目录（需含 河南方言语音板.exe），请先用 PyInstaller 打包")
candidates.sort(reverse=True)
DIST_DIR = candidates[0][1]
print(f"打包源目录：{DIST_DIR}")

ver = datetime.date.today().strftime("%Y%m%d")
zip_name = os.path.join(ROOT, f"河南方言语音板_v{ver}.zip")
docs = [
    (os.path.join(ROOT, "docs", "README.md"), "README.md"),
    (os.path.join(ROOT, "docs", "河南方言语音板_发布说明.md"), "河南方言语音板_发布说明.md"),
    (os.path.join(ROOT, "docs", "LICENSE"), "LICENSE"),
    (os.path.join(ROOT, ".env.example"), ".env.example"),
]

with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as z:
    # 打包整个 dist/河南方言语音板/ 文件夹（结构置于 zip 根：河南方言语音板/...）
    for root, dirs, files in os.walk(DIST_DIR):
        for f in files:
            fp = os.path.join(root, f)
            arc = os.path.join("河南方言语音板", os.path.relpath(fp, DIST_DIR))  # zip 顶层统一为 河南方言语音板/
            z.write(fp, arc)
    for p, arc in docs:
        if os.path.exists(p):
            z.write(p, arc)
        else:
            print(f"警告：文档缺失，跳过 {arc} -> {p}")

print(f"已生成分发包：{zip_name}  ({os.path.getsize(zip_name)} bytes)")
