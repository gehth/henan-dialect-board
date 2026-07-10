#!/usr/bin/env bash
# 单连接断点续传下载（无多进程、无重置）。
# 失败只续传(-C -)，不删除已下部分；外层循环校验最终大小，不到则重试。
set -u
cd "$(dirname "$0")" || exit 1
URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-paraformer-zh-2023-09-14.tar.bz2"
OUT="paraformer-zh.tar.bz2"
EXPECT=234051698   # 官方包字节数
MAX_LOOP=30
i=0
while [ "$i" -lt "$MAX_LOOP" ]; do
  i=$((i+1))
  echo "[$(date +%H:%M:%S)] 第 $i 次尝试 (已下 $(stat -c%s "$OUT" 2>/dev/null || echo 0) / $EXPECT 字节)"
  curl -L -C - --retry 15 --retry-all-errors --retry-delay 3 --connect-timeout 30 \
       -o "$OUT" "$URL" 2>&1 | tail -3
  sz=$(stat -c%s "$OUT" 2>/dev/null || echo 0)
  if [ "$sz" -ge "$EXPECT" ]; then
    echo "[$(date +%H:%M:%S)] 下载完成，大小正确: $sz"
    exit 0
  fi
  echo "[$(date +%H:%M:%S)] 未达标($sz/$EXPECT)，续传中..."
  sleep 2
done
echo "[$(date +%H:%M:%S)] 达到最大重试次数仍未完成，退出码 1"
exit 1
