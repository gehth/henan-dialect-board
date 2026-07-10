@echo off
chcp 65001 >nul
cd /d %~dp0

REM ============================================================
REM  河南方言语音板 · 桌面应用打包为单文件 exe
REM  先激活虚拟环境（含 PySide6/sounddevice/numpy/requests/
REM        python-dotenv/pypinyin/websocket-client/edge-tts/pyinstaller）
REM  用法：双击本文件即可（会自动覆盖旧 exe）
REM ============================================================

pyinstaller --noconfirm --noconsole --onedir --name "河南方言语音板" ^
  --add-data "dialect_dict.json;." ^
  --add-data "assets;assets" ^
  --collect-all PySide6 ^
  --collect-all edge_tts ^
  --collect-data pypinyin ^
  --exclude-module PySide6.Qt3DAnimation ^
  --exclude-module PySide6.Qt3DCore ^
  --exclude-module PySide6.Qt3DExtras ^
  --exclude-module PySide6.Qt3DInput ^
  --exclude-module PySide6.Qt3DLogic ^
  --exclude-module PySide6.Qt3DRender ^
  --exclude-module PySide6.Qt3DQuick ^
  --exclude-module PySide6.QtCharts ^
  --exclude-module PySide6.QtDataVisualization ^
  --exclude-module PySide6.QtQuick ^
  --exclude-module PySide6.QtQuickControls2 ^
  --exclude-module PySide6.QtQuickWidgets ^
  --exclude-module PySide6.QtQml ^
  --exclude-module PySide6.QtQmlModels ^
  --exclude-module PySide6.QtQmlWorkerScript ^
  --exclude-module PySide6.QtLocation ^
  --exclude-module PySide6.QtBluetooth ^
  --exclude-module PySide6.QtNfc ^
  --exclude-module PySide6.QtSerialPort ^
  --exclude-module PySide6.QtPositioning ^
  --exclude-module PySide6.QtWebEngineCore ^
  --exclude-module PySide6.QtWebEngineWidgets ^
  --exclude-module PySide6.QtWebEngineQuick ^
  --exclude-module PySide6.QtPdf ^
  --exclude-module PySide6.QtPdfWidgets ^
  --exclude-module PySide6.QtPrintSupport ^
  --exclude-module PySide6.QtScxml ^
  --exclude-module PySide6.QtStateMachine ^
  --exclude-module PySide6.QtSensors ^
  --exclude-module PySide6.QtHelp ^
  --exclude-module PySide6.QtDesigner ^
  --exclude-module PySide6.QtUiTools ^
  --exclude-module PySide6.QtXmlPatterns ^
  --exclude-module PySide6.QtTest ^
  --exclude-module PySide6.QtNetworkAuth ^
  --exclude-module PySide6.QtRemoteObjects ^
  --exclude-module PyQt5 ^
  --exclude-module PyQt6 ^
  main.py

echo.
echo 打包完成，exe 位于 dist\ 目录。
pause
