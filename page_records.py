#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""我的记录页：历史（自动记录）与收藏（手动）两个 tab，可回看、删单条、清空。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QTabWidget, QMessageBox,
)

import store
import theme


class RecordsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        t = QLabel("📜 我的记录")
        t.setObjectName("title")
        sub = QLabel("解析过的方言会自动存进历史；点「⭐ 收藏」的会进收藏。数据只存在你本机，不上传。")
        sub.setObjectName("sub")
        root.addWidget(t); root.addWidget(sub)

        tabs = QTabWidget()
        tabs.setStyleSheet("QTabWidget::tab-bar { alignment: left; }")

        # 历史
        hist = QWidget()
        self._build_tab(hist, "history")
        # 收藏
        fav = QWidget()
        self._build_tab(fav, "favorites")

        tabs.addTab(hist, "🕘 历史")
        tabs.addTab(fav, "⭐ 收藏")
        root.addWidget(tabs, 1)

        # 详情
        det = QFrame(objectName="panel")
        det.setFrameShape(QFrame.NoFrame)
        dv = QVBoxLayout(det)
        dv.setContentsMargins(16, 16, 16, 16)
        dv.setSpacing(8)
        self.detail = QLabel("点击左侧任意一条，这里显示完整内容。")
        self.detail.setWordWrap(True)
        self.detail.setTextFormat(Qt.RichText)
        self.detail.setStyleSheet(f"color:{theme.TXT_DIM};font-size:13px;line-height:1.7;")
        dv.addWidget(self.detail)
        root.addWidget(det)

    def _build_tab(self, widget, kind):
        v = QVBoxLayout(widget)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        head = QHBoxLayout()
        cnt = QLabel("")
        cnt.setStyleSheet(f"color:{theme.TXT_DIM};font-size:12px;")
        setattr(self, f"_{kind}_count", cnt)
        head.addWidget(cnt)
        head.addStretch(1)
        clear = QPushButton("清空")
        clear.clicked.connect(lambda _: self._clear(kind))
        head.addWidget(clear)
        v.addLayout(head)

        area = QScrollArea()
        area.setWidgetResizable(True)
        listw = QWidget()
        setattr(self, f"_{kind}_list", listw)
        lw = QVBoxLayout(listw)
        lw.setContentsMargins(0, 0, 0, 0)
        lw.setSpacing(8)
        lw.addStretch(1)
        area.setWidget(listw)
        v.addWidget(area, 1)

    def refresh(self):
        self._fill("history", store.get_history())
        self._fill("favorites", store.get_favorites())

    def _fill(self, kind, items):
        listw = getattr(self, f"_{kind}_list")
        # 清空旧内容（保留末尾 stretch）
        layout = listw.layout()
        for i in reversed(range(layout.count())):
            w = layout.itemAt(i).widget()
            if w is not None and w is not layout.itemAt(layout.count() - 1).widget():
                w.deleteLater()
        cnt = getattr(self, f"_{kind}_count")
        cnt.setText(f"共 {len(items)} 条")
        for it in items:
            row = self._row(it, kind)
            layout.insertWidget(layout.count() - 1, row)

    def _row(self, item, kind):
        frame = QFrame()
        frame.setStyleSheet(f"background:{theme.PANEL2};border:1px solid {theme.LINE};border-radius:8px;")
        h = QHBoxLayout(frame)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(3)
        d = QLabel(item.get("dialect", ""))
        d.setStyleSheet(f"color:{theme.TITLE};font-size:15px;font-weight:700;")
        m = QLabel(item.get("mandarin", ""))
        m.setStyleSheet(f"color:{theme.TXT_DIM};font-size:12.5px;")
        left.addWidget(d); left.addWidget(m)
        h.addLayout(left, 1)

        ts = QLabel(item.get("ts", ""))
        ts.setStyleSheet(f"color:{theme.TXT_DIM};font-size:11px;")
        h.addWidget(ts)

        view = QPushButton("查看")
        view.clicked.connect(lambda _: self._show(item))
        h.addWidget(view)

        delbtn = QPushButton("✕")
        delbtn.setFixedWidth(34)
        delbtn.clicked.connect(lambda _: self._delete(item, kind))
        h.addWidget(delbtn)
        return frame

    def _show(self, item):
        self._current_item = item
        wp = item.get("word_pinyin") or ""
        expl = item.get("explanation") or ""
        html = (
            f'<div style="color:{theme.GREEN};font-size:12px;font-weight:700;">方言原句</div>'
            f'<div style="color:{theme.TITLE};font-size:18px;font-weight:700;margin:2px 0 8px;">{item.get("dialect","")}</div>'
            + (f'<div style="color:{theme.GREEN};font-size:12px;font-weight:700;">逐词拼音</div>'
               f'<div style="color:{theme.TXT_DIM};font-size:14px;margin:2px 0 8px;">{wp}</div>' if wp else "")
            + f'<div style="color:{theme.GREEN};font-size:12px;font-weight:700;">普通话</div>'
              f'<div style="color:{theme.TXT_DIM};font-size:15px;margin:2px 0 8px;">{item.get("mandarin","")}</div>'
            + (f'<div style="color:{theme.GREEN};font-size:12px;font-weight:700;">拼音</div>'
               f'<div style="color:{theme.TXT_DIM};font-size:14px;margin:2px 0 8px;">{item.get("pinyin","")}</div>' if item.get("pinyin") else "")
            + f'<div style="color:{theme.GREEN};font-size:12px;font-weight:700;">释义</div>'
              f'<div style="color:{theme.TXT_DIM};font-size:13.5px;line-height:1.7;">{expl}</div>'
        )
        self.detail.setText(html)

    def _delete(self, item, kind):
        if kind == "history":
            store.remove_history(item.get("id"))
        else:
            store.remove_favorite(item.get("dialect", ""))
        self.refresh()

    def _clear(self, kind):
        if kind == "history":
            store.clear_history()
        else:
            store.clear_favorites()
        self.detail.setText("已清空。")
        self.refresh()

    # ----------------------------- 换肤 -----------------------------
    def apply_theme(self):
        """主题切换时由 MainWindow 调用：重渲染当前详情 HTML 并重建列表行（按当前主题色）。"""
        if getattr(self, "_current_item", None):
            self._show(self._current_item)
        self.refresh()
