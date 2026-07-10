#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""方言画廊：展示 AI 乡土插画卡片（弄啥嘞/得劲儿/中不中/烩面），可保存图片。"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea,
    QFileDialog, QGridLayout, QMessageBox,
)

import backend
import theme


# 插画清单（与 assets/illustrations 对应）
_ILLUS = [
    ("assets/illustrations/nongshale.png", "弄啥嘞", "nòng shá lei", "干什么呢"),
    ("assets/illustrations/deijin.png", "得劲儿", "dé jìnr", "舒服 / 合适 / 好"),
    ("assets/illustrations/zhongbuzhong.png", "中不中", "zhōng bù zhōng", "行不行 / 可不可以"),
    ("assets/illustrations/huimian.png", "烩面", "huì miàn", "河南招牌面食"),
]


class GalleryPage(QWidget):
    def __init__(self):
        super().__init__()
        self._cards = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        t = QLabel("🖼 方言画廊")
        t.setObjectName("title")
        sub = QLabel("AI 绘制的乡土插画，配上方言卡片。右键思路：把方言画进生活场景，记得更牢。")
        sub.setObjectName("sub")
        root.addWidget(t); root.addWidget(sub)

        grid = QGridLayout()
        grid.setSpacing(14)
        for i, (rel, name, py, mean) in enumerate(_ILLUS):
            grid.addWidget(self._card(rel, name, py, mean), i // 2, i % 2)
        root.addLayout(grid)
        root.addStretch(1)

    def _card(self, rel, name, py, mean):
        frame = QFrame(objectName="panel")
        frame.setFrameShape(QFrame.NoFrame)
        v = QVBoxLayout(frame)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        lab = QLabel()
        lab.setAlignment(Qt.AlignCenter)
        path = backend.resource_path(rel)
        if os.path.exists(path):
            pm = QPixmap(path).scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lab.setPixmap(pm)
        else:
            lab.setText("（插画缺失）")
            lab.setStyleSheet(f"color:{theme.TXT_DIM};")
        v.addWidget(lab)

        title = QLabel(name)
        title.setStyleSheet(f"color:{theme.TITLE};font-size:18px;font-weight:700;")
        title.setAlignment(Qt.AlignCenter)
        v.addWidget(title)

        piny = QLabel(py)
        piny.setStyleSheet(f"color:{theme.GREEN};font-size:13px;")
        piny.setAlignment(Qt.AlignCenter)
        v.addWidget(piny)

        desc = QLabel(mean)
        desc.setStyleSheet(f"color:{theme.TXT_DIM};font-size:12.5px;")
        desc.setAlignment(Qt.AlignCenter)
        v.addWidget(desc)

        save = QPushButton("💾 保存这张图")
        save.clicked.connect(lambda _checked, p=path: self._save(p))
        v.addWidget(save)
        self._cards.append((title, piny, desc, lab))
        return frame

    def _save(self, path):
        if not os.path.exists(path):
            QMessageBox.information(self, "提示", "插画文件缺失，无法保存。")
            return
        dest, _ = QFileDialog.getSaveFileName(self, "保存插画", os.path.basename(path), "PNG (*.png)")
        if dest:
            QPixmap(path).save(dest, "PNG")
            QMessageBox.information(self, "已保存", f"插画已保存到：\n{dest}")

    # ----------------------------- 换肤 -----------------------------
    def apply_theme(self):
        """主题切换时由 MainWindow 调用：重设插画卡片标题/拼音/释义颜色。"""
        for title, piny, desc, lab in getattr(self, "_cards", []):
            title.setStyleSheet(f"color:{theme.TITLE};font-size:18px;font-weight:700;")
            piny.setStyleSheet(f"color:{theme.GREEN};font-size:13px;")
            desc.setStyleSheet(f"color:{theme.TXT_DIM};font-size:12.5px;")
            if lab.text() == "（插画缺失）":
                lab.setStyleSheet(f"color:{theme.TXT_DIM};")
