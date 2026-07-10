# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all

# 词库多包聚合：打包所有 dialect_dict*.json（排除 .bak），便于 M2 多包扩展
import glob as _glob
datas = [(j, '.') for j in _glob.glob('dialect_dict*.json')]
datas += [('assets', 'assets')]
binaries = []
hiddenimports = ['asr', 'asr.base', 'asr.funasr_onnx_engine', 'asr.__init__', 'scipy',
                 'backend', 'backend._state', 'backend.pinyin', 'backend.dictionary',
                 'backend.demo', 'backend.llm', 'backend.config', 'backend.tts',
                 'backend.correct', 'backend.asr', 'backend.status']
datas += collect_data_files('pypinyin')
tmp_ret = collect_all('PySide6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('edge_tts')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# 离线识别运行时：用 collect_all 确保原生 DLL 一并被收集
# （onnxruntime 的 onnxruntime_providers_*.dll、kaldi_native_fbank 扩展、soundfile 的 libsndfile 均通过 ctypes 懒加载，hiddenimports 无法收集其二进制）
tmp_ret = collect_all('onnxruntime')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('kaldi_native_fbank')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('soundfile')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.Qt3DAnimation', 'PySide6.Qt3DCore', 'PySide6.Qt3DExtras', 'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DRender', 'PySide6.Qt3DQuick', 'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtQuick', 'PySide6.QtQuickControls2', 'PySide6.QtQuickWidgets', 'PySide6.QtQml', 'PySide6.QtQmlModels', 'PySide6.QtQmlWorkerScript', 'PySide6.QtLocation', 'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtSerialPort', 'PySide6.QtPositioning', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtPrintSupport', 'PySide6.QtScxml', 'PySide6.QtStateMachine', 'PySide6.QtSensors', 'PySide6.QtHelp', 'PySide6.QtDesigner', 'PySide6.QtUiTools', 'PySide6.QtXmlPatterns', 'PySide6.QtTest', 'PySide6.QtNetworkAuth', 'PySide6.QtRemoteObjects', 'PyQt5', 'PyQt6'],
    noarchive=False,
    optimize=1,
)
# 进一步排除运行时不使用的 Qt 高级模块（缩减体积，避免运行时按需加载无关库）
a.excludes += [
    'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets', 'PySide6.QtGraphicalEffects',
    'PySide6.QtVirtualKeyboard', 'PySide6.QtLottie', 'PySide6.QtTextToSpeech',
    'PySide6.QtHttpServer', 'PySide6.QtShaderTools',
    'PySide6.QtQuick3D', 'PySide6.QtQuick3DRuntimeRender',
    'PySide6.QtQuick3DAssetImport', 'PySide6.QtQuick3DUtils',
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='河南方言语音板',
    icon='app.ico',  # 扁平极简绿底白话筒 + 声波
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Windows 无 strip 工具；Qt 包体积由 Qt6 dll 主导，strip 收益极小
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,  # Windows 无 strip 工具；保留开关以备 Linux/macOS 交叉构建
    upx=True,
    upx_exclude=[],
    # 输出目录名由环境变量指定，默认 河南方言语音板_build。
    # 每次打包用全新时间戳目录名可彻底避开 Defender/索引服务持锁导致的
    # "清空旧目录 PermissionError"：新目录不存在→PyInstaller 跳过清理→不碰被锁文件。
    name=os.environ.get('HB_BUILD_DIR', '河南方言语音板_build'),
)
