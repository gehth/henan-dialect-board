#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习互动模块：三种模式
  1) 猜方言  —— 听到/看到一句河南话，从 4 个普通话选项中选正确释义，含计分与 TTS 朗读；
               答错时自动记入「错词本」，便于重点复习。
  2) 学习卡  —— 浏览方言词条（方言 / 拼音 / 普通话 / 解释 / 分类），可上下翻、朗读。
  3) 错词本  —— 复习答错的词条（同样卡片形式），可单条移除或一键清空。
"""
import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QStackedWidget,
)

import backend
import store
import theme

try:
    from PySide6.QtTextToSpeech import QTextToSpeech
except Exception:
    QTextToSpeech = None


class GamePage(QWidget):
    def __init__(self):
        super().__init__()
        self.phrases = [p for p in backend.get_dict().get("phrases", []) if p.get("mandarin")]
        self.score = 0
        self.total = 0
        self.cur = None
        self.options = []
        self._tts = None
        if QTextToSpeech:
            try:
                self._tts = QTextToSpeech()
            except Exception:
                self._tts = None
        # 学习卡浏览顺序（洗牌）
        self.card_order = list(self.phrases)
        random.shuffle(self.card_order)
        self.card_idx = 0
        self._build()
        self._switch_mode(0)

    # ----------------------------- 总装 -----------------------------
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        t = QLabel("🎮 学习互动")
        t.setObjectName("title")
        sub = QLabel("猜方言练手感、学习卡背词条、错词本重点复习。")
        sub.setObjectName("sub")
        root.addWidget(t)
        root.addWidget(sub)

        # 模式 segmented 控制
        self.mode_btns = []
        seg = QHBoxLayout()
        seg.setSpacing(8)
        for i, label in enumerate(["猜方言", "学习卡", "错词本"]):
            b = QPushButton(label, objectName="seg")
            b.clicked.connect(lambda _c, idx=i: self._switch_mode(idx))
            seg.addWidget(b)
            self.mode_btns.append(b)
        root.addLayout(seg)

        self.stack = QStackedWidget()
        self.game_w = self._build_game()
        self.card_w = self._build_card("card")
        self.wrong_w = self._build_card("wrong")
        self.stack.addWidget(self.game_w)
        self.stack.addWidget(self.card_w)
        self.stack.addWidget(self.wrong_w)
        root.addWidget(self.stack, 1)

    def _switch_mode(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx == 1:
            self._card_load()
        elif idx == 2:
            self._wrong_load()
        for i, b in enumerate(self.mode_btns):
            b.setProperty("active", i == idx)
            b.style().unpolish(b)
            b.style().polish(b)

    # ----------------------------- 猜方言 -----------------------------
    def _build_game(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        self.score_lab = QLabel("得分 0 / 0")
        self.score_lab.setObjectName("section")
        v.addWidget(self.score_lab)

        card = QFrame(objectName="panel")
        card.setFrameShape(QFrame.NoFrame)
        cv = QVBoxLayout(card)
        cv.setContentsMargins(18, 18, 18, 18)
        cv.setSpacing(12)

        ql = QLabel("这句河南话是啥意思？")
        ql.setStyleSheet(f"color:{theme.TXT_DIM};font-size:12px;")
        cv.addWidget(ql)

        self.g_dialect = QLabel("—")
        self.g_dialect.setStyleSheet(f"color:{theme.TITLE};font-size:30px;font-weight:700;")
        self.g_dialect.setAlignment(Qt.AlignCenter)
        cv.addWidget(self.g_dialect)

        speak = QPushButton("🔊 朗读这句方言")
        speak.clicked.connect(self._speak_game)
        cv.addWidget(speak, alignment=Qt.AlignCenter)

        self.g_opt_layout = QVBoxLayout()
        self.g_opt_layout.setSpacing(10)
        cv.addLayout(self.g_opt_layout)
        v.addWidget(card)

        row = QHBoxLayout()
        self.g_feedback = QLabel("")
        self.g_feedback.setStyleSheet(f"color:{theme.TXT_DIM};font-size:13px;")
        row.addWidget(self.g_feedback)
        row.addStretch(1)
        self.g_next = QPushButton("下一题 →", objectName="primary")
        self.g_next.clicked.connect(self.next_question)
        row.addWidget(self.g_next)
        v.addLayout(row)
        return w

    def next_question(self):
        if not self.phrases:
            return
        self.cur = random.choice(self.phrases)
        correct = self.cur["mandarin"].split(" / ")[0]
        others = []
        for p in self.phrases:
            m = p["mandarin"].split(" / ")[0]
            if m != correct and m not in others:
                others.append(m)
        random.shuffle(others)
        distractors = others[:3]
        while len(distractors) < 3:
            distractors.append("（略）")
        opts = distractors + [correct]
        random.shuffle(opts)
        self.options = opts

        self._answered = False
        self._correct = None
        self.g_dialect.setText(self.cur["dialect"])
        self.g_feedback.setText("")
        for i in reversed(range(self.g_opt_layout.count())):
            wgt = self.g_opt_layout.itemAt(i).widget()
            if wgt:
                wgt.deleteLater()
        self._opt_btns = []
        for opt in opts:
            b = QPushButton(opt)
            b.clicked.connect(lambda _checked, o=opt: self._answer(o))
            self.g_opt_layout.addWidget(b)
            self._opt_btns.append(b)

    def _answer(self, chosen):
        if self.cur is None or getattr(self, "_answered", False):
            return
        correct = self.cur["mandarin"].split(" / ")[0]
        self.total += 1
        self._answered = True
        self._correct = correct
        if chosen == correct:
            self.score += 1
            self.g_feedback.setText("✅ 答对了！")
            self.g_feedback.setStyleSheet(f"color:{theme.GREEN};font-size:13px;")
        else:
            self.g_feedback.setText(f"❌ 正确答案是：{correct}")
            self.g_feedback.setStyleSheet(f"color:{theme.TXT_DIM};font-size:13px;")
            # 记入错词本
            try:
                store.add_wrong_word(self.cur)
            except Exception:
                pass
        self.score_lab.setText(f"得分 {self.score} / {self.total}")
        for b in getattr(self, "_opt_btns", []):
            b.setEnabled(False)
            if b.text() == correct:
                b.setStyleSheet(f"border:1px solid {theme.GREEN};color:{theme.GREEN};")

    def _speak_game(self):
        if self._tts is None or not self.cur:
            return
        try:
            self._tts.say(self.cur["dialect"])
        except Exception:
            pass

    # --------------------- 通用卡片（学习卡 / 错词本） ---------------------
    def _build_card(self, kind):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        body = QFrame(objectName="panel")
        body.setFrameShape(QFrame.NoFrame)
        bv = QVBoxLayout(body)
        bv.setContentsMargins(20, 20, 20, 20)
        bv.setSpacing(10)

        dialect = QLabel("—")
        dialect.setAlignment(Qt.AlignCenter)
        dialect.setStyleSheet(f"color:{theme.TITLE};font-size:34px;font-weight:700;")
        pinyin = QLabel("")
        pinyin.setAlignment(Qt.AlignCenter)
        pinyin.setStyleSheet(f"color:{theme.GREEN};font-size:16px;")
        mandarin = QLabel("")
        mandarin.setAlignment(Qt.AlignCenter)
        mandarin.setStyleSheet(f"color:{theme.TXT};font-size:18px;font-weight:600;")
        expl = QLabel("")
        expl.setWordWrap(True)
        expl.setStyleSheet(f"color:{theme.TXT_DIM};font-size:13px;")
        cat = QLabel("")
        cat.setAlignment(Qt.AlignCenter)
        cat.setStyleSheet(f"color:{theme.TXT_DIM};font-size:12px;")
        bv.addWidget(dialect)
        bv.addWidget(pinyin)
        bv.addSpacing(6)
        bv.addWidget(mandarin)
        bv.addWidget(expl)
        bv.addStretch(1)
        bv.addWidget(cat)
        v.addWidget(body, 1)

        # 控制区
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)
        speak = QPushButton("🔊 朗读")
        speak.clicked.connect(lambda _c: self._speak_card(kind))
        ctrl.addWidget(speak)
        ctrl.addStretch(1)
        prev = QPushButton("← 上一个")
        prev.clicked.connect(lambda _c: self._card_step(kind, -1))
        ctrl.addWidget(prev)
        nxt = QPushButton("下一个 →")
        nxt.clicked.connect(lambda _c: self._card_step(kind, 1))
        ctrl.addWidget(nxt)
        v.addLayout(ctrl)

        if kind == "wrong":
            foot = QHBoxLayout()
            foot.setSpacing(8)
            self.w_count = QLabel("")
            self.w_count.setStyleSheet(f"color:{theme.TXT_DIM};font-size:12px;")
            foot.addWidget(self.w_count)
            foot.addStretch(1)
            rm = QPushButton("移除这条")
            rm.clicked.connect(self._wrong_remove)
            foot.addWidget(rm)
            clr = QPushButton("清空错词本")
            clr.clicked.connect(self._wrong_clear)
            foot.addWidget(clr)
            v.addLayout(foot)

        # 保存引用
        if kind == "card":
            self.c_dialect, self.c_pinyin, self.c_mandarin, self.c_expl, self.c_cat = (
                dialect, pinyin, mandarin, expl, cat)
        else:
            self.w_dialect, self.w_pinyin, self.w_mandarin, self.w_expl, self.w_cat = (
                dialect, pinyin, mandarin, expl, cat)
            self.w_empty = QLabel("🎉 错词本是空的，去「猜方言」练练手吧！")
            self.w_empty.setAlignment(Qt.AlignCenter)
            self.w_empty.setStyleSheet(f"color:{theme.TXT_DIM};font-size:15px;")
            self.w_empty.setVisible(False)
            v.insertWidget(0, self.w_empty)
        return w

    def _render(self, labels, phrase):
        if not phrase:
            return
        d, py, m, ex, ct = labels
        d.setText(phrase.get("dialect", "—"))
        py.setText(phrase.get("pinyin", ""))
        m.setText("普通话：" + phrase.get("mandarin", ""))
        ex.setText(phrase.get("explanation", ""))
        ct.setText("分类：" + phrase.get("category", "未分类"))

    def _card_load(self):
        if not self.card_order:
            return
        self.card_idx = max(0, min(self.card_idx, len(self.card_order) - 1))
        self._render((self.c_dialect, self.c_pinyin, self.c_mandarin, self.c_expl, self.c_cat),
                     self.card_order[self.card_idx])

    def _card_step(self, kind, delta):
        if kind == "card":
            if not self.card_order:
                return
            self.card_idx = (self.card_idx + delta) % len(self.card_order)
            self._render((self.c_dialect, self.c_pinyin, self.c_mandarin, self.c_expl, self.c_cat),
                         self.card_order[self.card_idx])
        else:
            self._wrong_step(delta)

    def _speak_card(self, kind):
        if self._tts is None:
            return
        if kind == "card" and self.card_order:
            txt = self.card_order[self.card_idx].get("dialect", "")
        elif kind == "wrong" and getattr(self, "_wrong_list", []):
            txt = self._wrong_list[self.w_idx].get("dialect", "")
        else:
            return
        if txt:
            try:
                self._tts.say(txt)
            except Exception:
                pass

    # ----------------------------- 错词本 -----------------------------
    def _wrong_load(self):
        self._wrong_list = store.get_wrong_words()
        self.w_idx = 0
        self._wrong_show()

    def _wrong_show(self):
        lst = getattr(self, "_wrong_list", [])
        if not lst:
            self.w_empty.setVisible(True)
            self.w_dialect.setText("")
            self.w_pinyin.setText("")
            self.w_mandarin.setText("")
            self.w_expl.setText("")
            self.w_cat.setText("")
            self.w_count.setText("")
            return
        self.w_empty.setVisible(False)
        self.w_idx = max(0, min(self.w_idx, len(lst) - 1))
        rec = lst[self.w_idx]
        self._render((self.w_dialect, self.w_pinyin, self.w_mandarin, self.w_expl, self.w_cat), rec)
        self.w_count.setText(f"第 {self.w_idx + 1} / {len(lst)} 条")

    def _wrong_step(self, delta):
        lst = getattr(self, "_wrong_list", [])
        if not lst:
            return
        self.w_idx = (self.w_idx + delta) % len(lst)
        self._wrong_show()

    def _wrong_remove(self):
        lst = getattr(self, "_wrong_list", [])
        if not lst:
            return
        rec = lst[self.w_idx]
        store.remove_wrong_word(rec.get("dialect", ""))
        self._wrong_load()

    def _wrong_clear(self):
        store.clear_wrong_words()
        self._wrong_load()

    # ----------------------------- 换肤 -----------------------------
    def apply_theme(self):
        self.g_dialect.setStyleSheet(f"color:{theme.TITLE};font-size:30px;font-weight:700;")
        for lbl in (self.c_dialect, self.w_dialect):
            lbl.setStyleSheet(f"color:{theme.TITLE};font-size:34px;font-weight:700;")
        for py in (self.c_pinyin, self.w_pinyin):
            py.setStyleSheet(f"color:{theme.GREEN};font-size:16px;")
        for m in (self.c_mandarin, self.w_mandarin):
            m.setStyleSheet(f"color:{theme.TXT};font-size:18px;font-weight:600;")
        for ex in (self.c_expl, self.w_expl):
            ex.setStyleSheet(f"color:{theme.TXT_DIM};font-size:13px;")
        if getattr(self, "_answered", False):
            if self.g_feedback.text().startswith("✅"):
                self.g_feedback.setStyleSheet(f"color:{theme.GREEN};font-size:13px;")
            else:
                self.g_feedback.setStyleSheet(f"color:{theme.TXT_DIM};font-size:13px;")
            for b in getattr(self, "_opt_btns", []):
                b.setEnabled(False)
                if b.text() == getattr(self, "_correct", None):
                    b.setStyleSheet(f"border:1px solid {theme.GREEN};color:{theme.GREEN};")
        else:
            self.g_feedback.setStyleSheet(f"color:{theme.TXT_DIM};font-size:13px;")
