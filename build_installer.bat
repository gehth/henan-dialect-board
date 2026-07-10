@echo off
REM ============================================================
REM 河南方言语音板 · 一键构建 setup.exe 安装包
REM 前置：已用 PyInstaller 打出 onedir 构建目录（dist/河南方言语音板_b*）
REM       并已安装 InnoSetup 6（winget install JRSoftware.InnoSetup）
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM 1) 自动挑选最新的瘦身构建目录（dist/河南方言语音板_b*，且含 exe）
set "SRC="
for /f "delims=" %%d in ('dir /b /ad /o-n "dist\河南方言语音板_b*" 2^>nul') do (
  if exist "dist\%%d\河南方言语音板.exe" (
    set "SRC=dist\%%d"
    goto :found
  )
)
:found
if not defined SRC (
  echo [ERROR] 未找到 dist\河南方言语音板_b* 构建目录，请先运行打包（make_dist.py）。
  exit /b 1
)
echo [INFO] 使用源目录: %SRC%

REM 2) 定位 InnoSetup 编译器 ISCC.exe
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo [ERROR] 未找到 InnoSetup ISCC.exe，请先安装：winget install JRSoftware.InnoSetup
  exit /b 1
)
echo [INFO] 使用编译器: %ISCC%

REM 3) 编译安装包（用 /DMySourceDir 覆盖脚本里的默认源目录）
"%ISCC%" /DMySourceDir="%SRC%" "installer\河南方言语音板_installer.iss"
if errorlevel 1 (
  echo [ERROR] ISCC 编译失败，请查看上方输出。
  exit /b 1
)
echo [OK] 安装包已生成: dist\河南方言语音板_setup.exe
endlocal
