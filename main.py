#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
河南方言语音板 · 桌面应用入口（PySide6 纯原生 GUI）
================================================
- 不再依赖浏览器/Flask，所有界面用 Qt 原生控件渲染
- 后端逻辑由 backend.py 直接调用；录音由 recorder.py（sounddevice）完成
- 历史/收藏/设置存于用户目录 ~/.henan_dialect/user_data.json
- v2.0：设置面板（主题/字号/识别引擎/TTS 音色/最小化到托盘）+ 亮色主题 + 系统托盘驻留

运行（开发）：
    pip install -r requirements.txt
    python main.py
打包：
    pyinstaller --noconsole --onefile --name "河南方言语音板" \
        --add-data "dialect_dict.json;." --add-data "assets;assets" main.py
"""
import os
import sys

# 编码兜底：部分 Windows 控制台为 GBK，遇到中文会崩
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QStatusBar, QGraphicsOpacityEffect,
    QSplashScreen, QDialog, QFormLayout, QComboBox, QCheckBox, QMessageBox,
    QSystemTrayIcon, QMenu, QLineEdit,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPointF, QSizeF, QRectF
from PySide6.QtGui import QPainter, QFont, QColor, QPixmap, QIcon, QAction, QPen

import backend
import theme
import store
from utils import mode_text
from version import __version__, REPO_URL, APP_NAME
from worker import Worker
from recorder import Recorder
from page_main import MainPage
from page_map import MapPage
from page_game import GamePage
from page_gallery import GalleryPage
from page_records import RecordsPage


class SettingsDialog(QDialog):
    """设置面板：主题 / 字号 / 识别引擎 / TTS 音色 / 大模型 / 最小化到托盘。"""

    THEME_OPTS = [("暗色", "dark"), ("亮色", "light")]
    SCALE_OPTS = [("标准", 1.0), ("大字号", 1.2), ("长辈模式", 1.4)]
    ENGINE_OPTS = [("自动（云端优先，其次离线）", "auto"),
                   ("离线 · FunASR-ONNX", "offline"),
                   ("云端 · 讯飞", "xunfei"),
                   ("本地 · FunASR(torch)", "funasr")]
    TTS_OPTS = [("普通话 · 晓晓（女）", "mandarin"),
                ("方言原句 · 云扬（男）", "dialect")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(420)
        s = store.get_settings()
        form = QFormLayout(self)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)

        self.theme_cb = QComboBox()
        for label, val in self.THEME_OPTS:
            self.theme_cb.addItem(label, val)
        self._set_current(self.theme_cb, s.get("theme", "dark"))
        form.addRow("主题", self.theme_cb)

        self.scale_cb = QComboBox()
        for label, val in self.SCALE_OPTS:
            self.scale_cb.addItem(label, val)
        self._set_current(self.scale_cb, s.get("font_scale", 1.0))
        form.addRow("字号", self.scale_cb)

        self.engine_cb = QComboBox()
        for label, val in self.ENGINE_OPTS:
            self.engine_cb.addItem(label, val)
        self._set_current(self.engine_cb, s.get("asr_engine", "auto"))
        form.addRow("识别引擎", self.engine_cb)

        self.tts_cb = QComboBox()
        for label, val in self.TTS_OPTS:
            self.tts_cb.addItem(label, val)
        self._set_current(self.tts_cb, s.get("tts_voice", "mandarin"))
        form.addRow("朗读音色", self.tts_cb)

        # ---- 大模型配置 ----
        cfg = backend.get_llm_config()
        self.key_edit = QLineEdit(cfg["llm_api_key"])
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("留空则使用内置词库兜底")
        form.addRow("大模型 API Key", self.key_edit)

        self.url_edit = QLineEdit(cfg["llm_base_url"] or "https://api.deepseek.com")
        self.url_edit.setPlaceholderText("OpenAI 兼容地址，如 https://api.deepseek.com 或 http://localhost:11434/v1")
        form.addRow("Base URL", self.url_edit)

        self.model_edit = QLineEdit(cfg["llm_model"] or "deepseek-chat")
        self.model_edit.setPlaceholderText("如 deepseek-chat / qwen-plus / qwen-max")
        form.addRow("模型名", self.model_edit)

        hint = QLabel("支持 DeepSeek、通义千问（DashScope 兼容模式）、本地 Ollama（填 http://localhost:11434/v1）。密钥仅存于本机 .env，不会上传。")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{theme.TXT_DIM};font-size:11px;")
        form.addRow(hint)

        self.tray_chk = QCheckBox("关闭窗口时最小化到系统托盘（不退出）")
        self.tray_chk.setChecked(bool(s.get("minimize_to_tray", False)))
        form.addRow(self.tray_chk)

        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton("确定", objectName="primary")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        row.addWidget(ok)
        form.addRow(row)

    @staticmethod
    def _set_current(cb, value):
        idx = cb.findData(value)
        if idx >= 0:
            cb.setCurrentIndex(idx)

    def selected(self) -> dict:
        return {
            "theme": self.theme_cb.currentData(),
            "font_scale": float(self.scale_cb.currentData()),
            "asr_engine": self.engine_cb.currentData(),
            "tts_voice": self.tts_cb.currentData(),
            "llm_api_key": self.key_edit.text().strip(),
            "llm_base_url": self.url_edit.text().strip(),
            "llm_model": self.model_edit.text().strip(),
            "minimize_to_tray": self.tray_chk.isChecked(),
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("河南方言语音板")
        self.resize(980, 680)
        self.recorder = Recorder()

        # 读取已保存的设置（主题/字号）
        self._theme = store.get_setting("theme", "dark")
        self._font_scale = float(store.get_setting("font_scale", 1.0))
        theme.set_theme(self._theme)
        self._force_quit = False

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 左侧导航
        nav = QWidget()
        nav.setFixedWidth(180)
        nav.setStyleSheet(f"background:{theme.PANEL};border-right:1px solid {theme.LINE};")
        nv = QVBoxLayout(nav)
        nv.setContentsMargins(0, 0, 0, 0)
        nv.setSpacing(0)
        brand = QLabel("河南方言\n语音板")
        brand.setStyleSheet(f"color:{theme.TITLE};font-size:17px;font-weight:700;padding:18px 16px 14px;")
        brand.setAlignment(Qt.AlignLeft)
        nv.addWidget(brand)

        self.nav_btns = []
        self.pages = []
        self.stack = QStackedWidget()

        entries = [
            ("🎤 语音板", MainPage),
            ("🗺 方言地图", MapPage),
            ("🎮 猜方言", GamePage),
            ("🖼 方言画廊", GalleryPage),
            ("📜 我的记录", RecordsPage),
        ]
        for i, (label, cls) in enumerate(entries):
            btn = QPushButton(label, objectName="nav")
            btn.clicked.connect(lambda _checked, idx=i: self._switch(idx))
            nv.addWidget(btn)
            self.nav_btns.append(btn)
            if cls is MainPage:
                page = cls(self.recorder)
                page.historyChanged.connect(self._on_history_changed)
            else:
                page = cls()
            self.stack.addWidget(page)
            self.pages.append(page)
        nv.addStretch(1)

        # 设置按钮
        settings_btn = QPushButton("⚙ 设置", objectName="elder")
        settings_btn.clicked.connect(self._on_settings)
        nv.addWidget(settings_btn)

        # 长辈模式开关
        self._elder = self._font_scale >= 1.4
        elder_btn = QPushButton("🔍 长辈模式：" + ("开" if self._elder else "关"), objectName="elder")
        elder_btn.clicked.connect(self._toggle_elder)
        nv.addWidget(elder_btn)
        self._elder_btn = elder_btn

        # 状态
        st = QLabel()
        st.setStyleSheet(f"color:{theme.TXT_DIM};font-size:11px;padding:12px 16px;")
        st.setText(mode_text(backend.get_status()))
        nv.addWidget(st)

        root.addWidget(nav)
        root.addWidget(self.stack, 1)

        # 状态栏
        sb = QStatusBar()
        sb.setStyleSheet(f"color:{theme.TXT_DIM};font-size:11px;")
        sb.showMessage(backend.get_status()["message"])
        self.setStatusBar(sb)

        # 托盘
        self._init_tray()

        # 帮助菜单（检查更新 / 关于）
        self._init_help_menu()

        self._nav = nav
        self._brand = brand
        self._st = st

        self._switch(0)

    # ----------------------------- 导航 -----------------------------
    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)
        w = self.stack.widget(idx)
        if w is not None:
            eff = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity")
            anim.setDuration(180)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setStartValue(0.15)
            anim.setEndValue(1.0)
            anim.finished.connect(lambda: w.setGraphicsEffect(None))
            self._fade = anim
            anim.start()
        for i, b in enumerate(self.nav_btns):
            b.setProperty("active", i == idx)
            b.style().unpolish(b)
            b.style().polish(b)

    def _on_history_changed(self):
        # 历史/收藏页刷新
        for p in self.pages:
            if hasattr(p, "refresh"):
                try:
                    p.refresh()
                except Exception:
                    pass

    # ----------------------------- 设置 -----------------------------
    def _on_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            sel = dlg.selected()
            # UI 设置持久化到 store
            for k in ("theme", "font_scale", "asr_engine", "tts_voice", "minimize_to_tray"):
                store.set_setting(k, sel[k])
            # 大模型：运行时立即生效 + 持久化到 .env（无需重启、无需手动改文件）
            backend.set_llm_config(sel["llm_api_key"], sel["llm_base_url"], sel["llm_model"])
            backend.save_llm_config_to_env(sel["llm_api_key"], sel["llm_base_url"], sel["llm_model"])
            self._apply_theme(sel["font_scale"], sel["theme"])
            self._apply_settings()

    def _apply_settings(self):
        """把设置中影响运行时的项（识别引擎 / TTS 默认音色）落到引擎与页面。"""
        backend.set_asr_engine(store.get_setting("asr_engine", "auto"))
        # 更新导航状态栏的识别方式文字
        self._st.setText(mode_text(backend.get_status()))
        # 刷新主页识别方式指示
        for p in self.pages:
            fn = getattr(p, "_refresh_asr_mode", None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass

    def _apply_theme(self, scale=None, theme_name=None):
        if theme_name is None:
            theme_name = self._theme
        if scale is None:
            scale = self._font_scale
        self._theme = theme_name
        self._font_scale = scale
        theme.set_theme(theme_name)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(theme.build_qss(scale, theme_name))
        # 导航栏 / 品牌 / 状态栏内联样式（主题色）
        self._nav.setStyleSheet(f"background:{theme.PANEL};border-right:1px solid {theme.LINE};")
        self._brand.setStyleSheet(f"color:{theme.TITLE};font-size:17px;font-weight:700;padding:18px 16px 14px;")
        self._st.setStyleSheet(f"color:{theme.TXT_DIM};font-size:11px;padding:12px 16px;")
        self.statusBar().setStyleSheet(f"color:{theme.TXT_DIM};font-size:11px;")
        # 各页换肤
        for p in self.pages:
            fn = getattr(p, "apply_theme", None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass

    def _toggle_elder(self):
        self._elder = not self._elder
        scale = 1.4 if self._elder else 1.0
        store.set_setting("font_scale", scale)
        self._apply_theme(scale, self._theme)
        self._elder_btn.setText("🔍 长辈模式：" + ("开" if self._elder else "关"))

    # ----------------------------- 托盘 -----------------------------
    def _init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = None
            return
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(_make_icon())
        self._tray.setToolTip("河南方言语音板")
        menu = QMenu(self)
        show_act = QAction("显示主窗口", self)
        show_act.triggered.connect(self._show_normal)
        check_act = QAction("检查更新", self)
        check_act.triggered.connect(self._check_update)
        quit_act = QAction("退出", self)
        quit_act.triggered.connect(self._quit)
        menu.addAction(show_act)
        menu.addAction(check_act)
        menu.addAction(quit_act)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda reason: self._show_normal() if reason == QSystemTrayIcon.DoubleClick else None
        )
        self._tray.show()

    def _show_normal(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit(self):
        """托盘菜单「退出」：强制真正退出（绕过最小化到托盘的 closeEvent 逻辑）。"""
        self._force_quit = True
        QApplication.instance().quit()

    def _init_help_menu(self):
        """菜单栏「帮助」：检查更新 / 关于。"""
        help_menu = self.menuBar().addMenu("帮助")
        check_act = QAction("检查更新", self)
        check_act.triggered.connect(self._check_update)
        help_menu.addAction(check_act)
        about_act = QAction("关于", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _check_update(self):
        """后台检查更新（非阻塞，优雅降级离线）。"""
        from backend.update_check import check_for_update
        url = store.get_setting("update_server_url", None)
        if getattr(self, "_upd_worker", None) and self._upd_worker.isRunning():
            return  # 已有检查在跑
        self.statusBar().showMessage("正在检查更新…")
        self._upd_worker = Worker(check_for_update, __version__, url)
        self._upd_worker.finished.connect(self._on_update_result)
        self._upd_worker.error.connect(self._on_update_error)
        self._upd_worker.start()

    def _on_update_result(self, info):
        if info.get("error"):
            self.statusBar().showMessage("检查更新失败")
            QMessageBox.information(
                self, "检查更新",
                f"无法检查更新：\n{info['error']}\n\n请确认网络后重试。")
            return
        if not info.get("update_available"):
            self.statusBar().showMessage(f"已是最新版本（v{info['current']}）")
            QMessageBox.information(self, "检查更新", f"当前已是最新版本 v{info['current']}。")
            return
        lines = [f"发现新版本 v{info['latest']}（当前 v{info['current']}）", ""]
        if info.get("summary"):
            lines.append(info["summary"]); lines.append("")
        if info.get("changelog"):
            lines.append("更新内容：")
            for c in info["changelog"]:
                lines.append(f"  · {c}")
            lines.append("")
        dls = info.get("downloads", {})
        if dls:
            lines.append("下载地址：")
            for k, v in dls.items():
                lines.append(f"  · {v.get('label', k)}：{v.get('url')}")
        msg = "\n".join(lines)
        self.statusBar().showMessage(f"发现新版本 v{info['latest']}")
        if info.get("force"):
            QMessageBox.warning(self, "重要更新", msg)
        else:
            QMessageBox.information(self, "发现新版本", msg)

    def _on_update_error(self, e):
        self.statusBar().showMessage("检查更新出错")
        QMessageBox.information(self, "检查更新", f"检查更新时出错：\n{e}")

    def _show_about(self):
        QMessageBox.about(
            self, "关于 河南方言语音板",
            f"{APP_NAME} v{__version__}\n\n"
            f"河南方言学习 · 识别 · 互动桌面应用\n\n"
            f"仓库：{REPO_URL}")

    def closeEvent(self, ev):
        if getattr(self, "_force_quit", False):
            ev.accept()
            return
        if getattr(self._tray, "isVisible", lambda: False)() and store.get_setting("minimize_to_tray", False):
            ev.ignore()
            self.hide()
            self._tray.showMessage("河南方言语音板", "已最小化到系统托盘，双击图标可恢复。",
                                   QSystemTrayIcon.Information, 2000)
        else:
            ev.accept()


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(_make_icon())
    # 应用保存的主题 / 字号（在构建界面前，确保各页用正确主题色构建）
    _s_theme = store.get_setting("theme", "dark")
    _s_scale = float(store.get_setting("font_scale", 1.0))
    theme.set_theme(_s_theme)
    app.setStyleSheet(theme.build_qss(_s_scale, _s_theme))

    splash = _make_splash()
    splash.show()
    app.processEvents()
    win = MainWindow()
    splash.finish(win)
    win.show()
    sys.exit(app.exec())


def _make_splash():
    pix = QPixmap(440, 260)
    pix.fill(QColor(theme.BG))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor(theme.GREEN))
    p.setFont(QFont("Microsoft YaHei", 26, QFont.Bold))
    p.drawText(pix.rect().adjusted(0, -30, 0, 0), Qt.AlignCenter, "河南方言语音板")
    p.setPen(QColor(theme.TXT_DIM))
    p.setFont(QFont("Microsoft YaHei", 13))
    p.drawText(pix.rect().adjusted(0, 40, 0, 0), Qt.AlignCenter, "正在加载方言词库与界面…")
    p.end()
    sp = QSplashScreen(pix)
    sp.setStyleSheet(f"QSplashScreen{{background:{theme.BG};}}")
    return sp


def _make_icon() -> QIcon:
    """生成扁平极简应用图标（圆角绿块 + 白色话筒 + 右侧声波弧）。"""
    S = 64
    pix = QPixmap(S, S)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # 背景：圆角绿块
    p.setBrush(QColor(theme.GREEN))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(4.5, 4.5, S - 9, S - 9, 14, 14)

    # 白色话筒
    cx = S / 2.0
    head_w, head_h = S * 0.22, S * 0.27
    head_top = S * 0.19

    # 头（胶囊）
    r_head = head_w / 2.0
    p.setBrush(Qt.white)
    p.drawRoundedRect(QRectF(cx - r_head, head_top, head_w, head_h), r_head, r_head)

    # 杆
    stem_w = S * 0.06
    stem_top = head_top + head_h - S * 0.01
    stem_bot = S * 0.55
    r_stem = stem_w / 2.0
    p.drawRoundedRect(QRectF(cx - r_stem, stem_top, stem_w, stem_bot - stem_top), r_stem, r_stem)

    # 底座横线
    base_y = stem_bot + S * 0.03
    base_w = S * 0.30
    p.setPen(QPen(Qt.white, max(1, S * 0.045)))
    p.drawLine(QPointF(cx - base_w / 2, base_y), QPointF(cx + base_w / 2, base_y))

    # 声波（右侧两条弧）
    cy_mid = head_top + head_h / 2.0
    pen_wave = QPen(QColor(255, 255, 255, 210), max(1, S * 0.022))
    p.setPen(pen_wave)
    for _k in (0.90, 1.35):
        R = head_w * _k
        rect = QRectF(cx - R, cy_mid - R, R * 2, R * 2)
        p.drawArc(rect, int(-65 * 16), int(130 * 16))

    p.end()
    return QIcon(pix)


if __name__ == "__main__":
    main()
