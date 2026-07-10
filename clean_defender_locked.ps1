# -*- coding: utf-8 -*-
<#
.SYNOPSIS
  以管理员身份删除被 Windows Defender 实时扫描持锁的历史构建目录。

.DESCRIPTION
  1. 若当前非管理员，自动用 RunAs 请求提权（弹出 UAC）。
  2. 将 3 个被锁的旧构建目录临时加入 Windows Defender 排除项。
  3. 等待 Defender 释放已有文件句柄后删除。
  4. 删除完成后移除临时排除项，恢复 Defender 实时防护。

.NOTES
  必须在你本机“以管理员身份运行”的 PowerShell 中执行（双击 .ps1 默认用记事本打开，
  请右键该文件 → “使用 PowerShell 运行”，或在管理员 PowerShell 里执行本脚本）。
  在 CodeBuddy 内置终端里跑会被 safe-delete 拦截且无法提权，故请在本机原生 PowerShell 执行。
#>

$ErrorActionPreference = 'Stop'

# ── 自动提权：非管理员则用 RunAs 重新启动本脚本 ──
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host '请求管理员权限(UAC)...' -ForegroundColor Yellow
    Start-Process PowerShell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

$root = 'G:\WorkBuddy专用文件夹\河南方言语音板'
$targets = @(
    Join-Path $root 'dist/河南方言语音板'
    Join-Path $root 'dist/河南方言语音板_b20260708_223534'
    Join-Path $root 'dist/河南方言语音板_b20260709_split2'
    Join-Path $root 'dist/河南方言语音板_build'
)

Write-Host "`n将被清理的目录（被 Defender 持锁的旧构建残留）：" -ForegroundColor Cyan
$targets | ForEach-Object { Write-Host "  $_" }

# 1) 临时加入 Defender 排除项
try {
    Add-MpPreference -ExclusionPath $targets
    Write-Host '✅ 已临时添加 Defender 排除项' -ForegroundColor Green
} catch {
    Write-Host "❌ 添加排除项失败（可能仍非管理员）：$_" -ForegroundColor Red
    Read-Host '按 Enter 退出'
    exit 1
}

# 2) 等待 Defender 释放已有句柄
Start-Sleep -Seconds 4

# 3) 删除残留（带重试，应对仍可能存在的短暂锁）
foreach ($p in $targets) {
    if (-not (Test-Path $p)) { Write-Host "∅ 已不存在，跳过: $p"; continue }
    $ok = $false
    for ($i = 1; $i -le 10; $i++) {
        try { [System.IO.Directory]::Delete($p, $true); $ok = $true; break }
        catch { Start-Sleep -Seconds 1 }
    }
    if ($ok -and -not (Test-Path $p)) { Write-Host "✅ 已删除: $p" -ForegroundColor Green }
    else { Write-Host "⚠ 仍残留（可重启后再跑一次本脚本）: $p" -ForegroundColor Yellow }
}

# 4) 移除临时排除项，恢复 Defender 实时防护
try {
    Remove-MpPreference -ExclusionPath $targets
    Write-Host '✅ 已移除 Defender 临时排除项，防护已恢复' -ForegroundColor Green
} catch {
    Write-Host '⚠ 移除排除项失败，请手动到 Windows Defender 设置中检查：' -ForegroundColor Yellow
    Write-Host $_.Exception.Message
}

$left = (Get-ChildItem $root\dist | Where-Object { $_.Name -in @('河南方言语音板','河南方言语音板_b20260708_223534','河南方言语音板_b20260709_split2','河南方言语音板_build') })
if ($left) {
    Write-Host "`n仍有残留目录未删除，建议重启电脑后再次运行本脚本。" -ForegroundColor Yellow
} else {
    Write-Host "`n🎉 全部历史构建目录已清理完毕。" -ForegroundColor Green
}
Read-Host '按 Enter 退出'
