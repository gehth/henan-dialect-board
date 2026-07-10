#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""方言地图页：用 QPainter 绘制河南轮廓与地市点位，点击查看当地说法特点与示例。"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea

import backend
import theme

# 河南轮廓多边形（与网页版一致，viewBox 0 0 680 480）
_POLY = [(310,55),(475,55),(510,120),(545,205),(515,255),(500,300),(470,360),
         (485,430),(430,455),(370,440),(300,400),(245,360),(210,290),(175,225),
         (200,160),(255,95)]
_VIEW_W, _VIEW_H = 680, 480


class MapView(QWidget):
    cityClicked = Signal(int)

    def __init__(self, cities):
        super().__init__()
        self.cities = cities
        self.selected = 0
        self._coords = []  # 屏幕坐标缓存
        self.setMinimumHeight(360)
        self.setMinimumWidth(420)

    def set_selected(self, i):
        self.selected = i
        self.update()

    def _transform(self):
        """把 viewBox 坐标映射到当前 widget 尺寸（保持比例 + 居中留白）。"""
        w = self.width(); h = self.height()
        pad = 24
        sx = (w - 2 * pad) / _VIEW_W
        sy = (h - 2 * pad) / _VIEW_H
        s = min(sx, sy)
        ox = (w - _VIEW_W * s) / 2
        oy = (h - _VIEW_H * s) / 2
        return s, ox, oy

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s, ox, oy = self._transform()

        # 轮廓
        poly = [QPointF(ox + x * s, oy + y * s) for (x, y) in _POLY]
        pp = QPen(QColor(theme.GREEN_DIM))
        pp.setWidth(2)
        p.setPen(pp)
        p.setBrush(QBrush(QColor(theme.PANEL2)))
        p.drawPolygon(poly)

        # 城市点位
        self._coords = []
        for i, c in enumerate(self.cities):
            cx = ox + c["x"] * s
            cy = oy + c["y"] * s
            self._coords.append((cx, cy))
            r = 7
            active = (i == self.selected)
            if active:
                p.setBrush(QBrush(QColor(theme.GREEN)))
                p.setPen(QPen(QColor(theme.TITLE)))
            else:
                p.setBrush(QBrush(QColor(theme.PANEL2)))
                p.setPen(QPen(QColor(theme.GREEN_DIM)))
            p.drawEllipse(QPointF(cx, cy), r, r)
            # 标签
            p.setPen(QPen(QColor(theme.GREEN if active else theme.TXT_DIM)))
            p.setFont(QFont("Microsoft YaHei", 11, QFont.Bold if active else QFont.Normal))
            p.drawText(int(cx) + 11, int(cy) + 4, c["name"])

    def mousePressEvent(self, ev):
        if not self._coords:
            return
        for i, (cx, cy) in enumerate(self._coords):
            dx = ev.position().x() - cx
            dy = ev.position().y() - cy
            if dx * dx + dy * dy <= 12 * 12:
                self.selected = i
                self.update()
                self.cityClicked.emit(i)
                return


class MapPage(QWidget):
    def __init__(self):
        super().__init__()
        self.cities = backend.get_dict().get("cities", [])
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        t = QLabel("🗺 河南方言地图")
        t.setObjectName("title")
        sub = QLabel("点击地图上的城市，看看当地的说法有啥不同。河南横跨中原官话、晋语与江淮官话过渡带，地市差异不小。")
        sub.setObjectName("sub")
        root.addWidget(t); root.addWidget(sub)

        layout = QHBoxLayout()
        layout.setSpacing(14)

        map_frame = QFrame(objectName="panel")
        map_frame.setFrameShape(QFrame.NoFrame)
        mf = QVBoxLayout(map_frame)
        mf.setContentsMargins(10, 10, 10, 10)
        self.map_view = MapView(self.cities)
        self.map_view.cityClicked.connect(self._on_city)
        mf.addWidget(self.map_view)
        legend = QLabel("示意图（城市点位为相对位置，非精确地理坐标）")
        legend.setStyleSheet(f"color:{theme.TXT_DIM};font-size:11px;text-align:center;")
        legend.setAlignment(Qt.AlignCenter)
        mf.addWidget(legend)
        self.legend = legend
        layout.addWidget(map_frame, 3)

        info_frame = QFrame(objectName="panel")
        info_frame.setFrameShape(QFrame.NoFrame)
        inf = QVBoxLayout(info_frame)
        inf.setContentsMargins(16, 16, 16, 16)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setTextFormat(Qt.RichText)
        inf.addWidget(self.info)
        layout.addWidget(info_frame, 2)

        root.addLayout(layout)
        if self.cities:
            self._on_city(0)

    def _on_city(self, idx):
        self.map_view.set_selected(idx)
        c = self.cities[idx]
        chips = "".join(f'<span style="display:inline-block;border:1px solid {theme.LINE};'
                        f'background:{theme.PANEL2};color:{theme.TXT};padding:4px 10px;'
                        f'border-radius:14px;font-size:12px;margin:3px 4px 3px 0;">{s}</span>'
                        for s in c.get("sayings", []))
        html = (
            f'<h2 style="margin:0 0 6px;color:{theme.GREEN};font-size:18px;">{c["name"]}</h2>'
            f'<div style="color:{theme.TXT_DIM};font-size:13px;line-height:1.7;margin:8px 0 14px;">{c.get("note","")}</div>'
            f'<div style="color:{theme.TXT_DIM};font-size:11px;letter-spacing:1px;margin-bottom:6px;">当地说法示例</div>'
            f'{chips}'
        )
        self.info.setText(html)

    # ----------------------------- 换肤 -----------------------------
    def apply_theme(self):
        """主题切换时由 MainWindow 调用：重绘地图 + 重渲染当前城市详情 HTML。"""
        self.legend.setStyleSheet(f"color:{theme.TXT_DIM};font-size:11px;text-align:center;")
        self.map_view.update()
        if self.cities:
            self._on_city(self.map_view.selected)
