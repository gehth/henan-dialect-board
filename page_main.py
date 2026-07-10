#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语音板主页：输入/示例 -> 解析 -> 普通话/拼音/逐词拼音/释义；录音 + 音量条；收藏；分享卡片；朗读。"""
import os

from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QTextOption
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QPlainTextEdit, QComboBox, QProgressBar, QMessageBox, QFileDialog,
    QDialog, QScrollArea, QListWidget, QLineEdit,
)

import backend
import store
from recorder import Recorder
from worker import Worker
from utils import run_worker
import theme

try:
    from PySide6.QtTextToSpeech import QTextToSpeech
except Exception:
    QTextToSpeech = None


class MainPage(QWidget):
    historyChanged = Signal()

    def __init__(self, recorder: Recorder):
        super().__init__()
        self.recorder = recorder
        self.current = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_level)
        self._tts = None
        if QTextToSpeech:
            try:
                self._tts = QTextToSpeech()
            except Exception:
                self._tts = None
        # 在线 TTS 播放器：Edge TTS 生成 mp3 后用 Qt 内置播放，无需外部播放器
        self._player = None
        try:
            self._player = QMediaPlayer()
            self._player.setAudioOutput(QAudioOutput())
        except Exception:
            self._player = None
        self._build_ui()

    # ----------------------------- UI -----------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        # 标题
        t = QLabel("河南方言语音板")
        t.setObjectName("title")
        sub = QLabel("说一句河南话，听听普通话咋说、拼音咋拼、到底是啥意思。")
        sub.setObjectName("sub")
        root.addWidget(t)
        root.addWidget(sub)

        # 输入区
        panel = QFrame(objectName="panel")
        panel.setFrameShape(QFrame.NoFrame)
        pv = QVBoxLayout(panel)
        pv.setContentsMargins(16, 16, 16, 16)
        pv.setSpacing(12)

        lbl = QLabel("输入方言（或选一句示例）")
        lbl.setObjectName("section")
        pv.addWidget(lbl)

        self.input = QPlainTextEdit(objectName="input")
        self.input.setPlaceholderText("例如：弄啥嘞 / 得劲儿 / 中不中 / 俺恁咱")
        self.input.setMaximumHeight(70)
        pv.addWidget(self.input)

        exrow = QHBoxLayout()
        exrow.addWidget(QLabel("示例："))
        self.example = QComboBox()
        self.example.setMinimumWidth(260)
        self.example.currentIndexChanged.connect(self._on_example)
        self._refresh_examples()
        exrow.addWidget(self.example)
        exrow.addStretch(1)
        pv.addLayout(exrow)

        # 按钮行
        brow = QHBoxLayout()
        brow.setSpacing(10)
        self.parse_btn = QPushButton("生成普通话 + 拼音 + 释义", objectName="primary")
        self.parse_btn.clicked.connect(self._on_parse)
        self.rec_btn = QPushButton("🎙 录音识别", objectName="rec")
        self.rec_btn.clicked.connect(self._on_rec)
        brow.addWidget(self.parse_btn)
        brow.addWidget(self.rec_btn)
        self.dict_btn = QPushButton("📚 我的词库", objectName="ghost")
        self.dict_btn.clicked.connect(self._on_open_dict)
        brow.addWidget(self.dict_btn)
        brow.addStretch(1)
        pv.addLayout(brow)

        # 音量条
        self.level = QProgressBar()
        self.level.setRange(0, 100)
        self.level.setValue(0)
        self.level.setFixedHeight(12)
        self.level.setFormat("")
        pv.addWidget(self.level)
        self.info = QLabel("")
        self.info.setStyleSheet(f"color:{theme.TXT_DIM};font-size:12px;")
        pv.addWidget(self.info)

        # 识别方式指示（离线/云端/未配置）
        self.asr_mode = QLabel("")
        self.asr_mode.setStyleSheet(f"color:{theme.GREEN};font-size:12px;font-weight:600;")
        pv.addWidget(self.asr_mode)

        root.addWidget(panel)

        # 结果区
        self.result = QFrame(objectName="panel")
        self.result.setFrameShape(QFrame.NoFrame)
        self.result.setVisible(False)
        rv = QVBoxLayout(self.result)
        rv.setContentsMargins(16, 16, 16, 16)
        rv.setSpacing(10)

        rtitle = QLabel("解析结果")
        rtitle.setObjectName("section")
        rv.addWidget(rtitle)

        self._sec_pairs = []
        def mk(label_text):
            lab = QLabel(label_text)
            lab.setStyleSheet(f"color:{theme.GREEN};font-size:12px;font-weight:700;")
            val = QLabel("—")
            val.setStyleSheet(f"color:{theme.TXT_DIM};font-size:15px;")
            val.setWordWrap(True)
            rv.addWidget(lab)
            rv.addWidget(val)
            self._sec_pairs.append((lab, val))
            return val

        self.r_dialect = QLabel("—")
        self.r_dialect.setStyleSheet(f"color:{theme.TITLE};font-size:18px;font-weight:700;")
        self.r_dialect.setWordWrap(True)
        rv.addWidget(QLabel("原句"))
        rv.addWidget(self.r_dialect)

        self.r_word_py = mk("逐词拼音（跟读）")
        self.r_mandarin = mk("普通话")
        self.r_pinyin = mk("整句拼音")
        self.r_expl = mk("释义")

        self.r_engine = QLabel("")
        self.r_engine.setStyleSheet(f"color:{theme.TXT_DIM};font-size:12px;")
        rv.addWidget(self.r_engine)

        # 操作行
        act = QHBoxLayout()
        self.fav_btn = QPushButton("⭐ 收藏", objectName="fav")
        self.fav_btn.setProperty("on", False)
        self.fav_btn.clicked.connect(self._on_fav)
        self.speak_mode = QComboBox()
        self.speak_mode.addItem("🔊 朗读普通话", "mandarin")
        self.speak_mode.addItem("🗣 朗读原句", "dialect")
        # 以设置中的 TTS 音色为默认
        _tv = store.get_setting("tts_voice", "mandarin")
        _idx = self.speak_mode.findData(_tv)
        if _idx >= 0:
            self.speak_mode.setCurrentIndex(_idx)
        self.speak_btn = QPushButton("▶ 朗读")
        self.speak_btn.clicked.connect(self._on_speak)
        self.card_btn = QPushButton("🃏 生成分享卡片")
        self.card_btn.clicked.connect(self._on_card)
        act.addWidget(self.fav_btn)
        act.addWidget(self.speak_btn)
        act.addWidget(self.card_btn)
        act.addStretch(1)
        rv.addLayout(act)

        root.addWidget(self.result)
        root.addStretch(1)

        # 初始化识别方式指示
        self._refresh_asr_mode()

    # ----------------------------- 交互 -----------------------------
    def _on_example(self, idx):
        v = self.example.currentData()
        if v:
            self.input.setPlainText(v)

    def _on_parse(self):
        text = self.input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "请先输入或选择一句方言。")
            return
        self.parse_btn.setEnabled(False)
        self.rec_btn.setEnabled(False)
        self.info.setText("解析中…")
        self._worker = run_worker(backend.process_text, text,
                                  on_finished=lambda r: self._on_parsed(r, ""),
                                  on_error=lambda e: self._on_error(e))

    def _on_parsed(self, result, engine_tag):
        self.parse_btn.setEnabled(True)
        self.rec_btn.setEnabled(True)
        self.current = result
        self.r_dialect.setText(result.get("dialect") or self.input.toPlainText().strip())
        self.r_word_py.setText(result.get("word_pinyin") or "—")
        self.r_mandarin.setText(result.get("mandarin") or "—")
        self.r_pinyin.setText(result.get("pinyin") or "—")
        self.r_expl.setText(result.get("explanation") or "—")
        src = result.get("source", "")
        if src.startswith("demo"):
            tag = "内置词库（演示兜底）"
        elif src == "llm":
            tag = "大模型生成"
        else:
            tag = "内置词库"
        self.r_engine.setText((engine_tag + " · " if engine_tag else "") + tag +
                              ("　|　释义由 AI 或内置词库生成，仅供参考" if engine_tag or src == "llm" else ""))
        self.result.setVisible(True)
        self._refresh_fav_btn()
        # 自动写入历史
        store.add_history(result)
        self.historyChanged.emit()
        self.info.setText("解析完成" + ("（演示模式）" if src.startswith("demo") else ""))

    def _on_error(self, msg):
        self.parse_btn.setEnabled(True)
        self.rec_btn.setEnabled(True)
        self.info.setText("")
        QMessageBox.warning(self, "出错了", msg)

    def _refresh_fav_btn(self):
        on = bool(self.current) and store.is_favorite(self.current.get("dialect", ""))
        self.fav_btn.setProperty("on", on)
        self.fav_btn.setText("⭐ 已收藏" if on else "⭐ 收藏")
        # 强制刷新样式
        self.fav_btn.style().unpolish(self.fav_btn)
        self.fav_btn.style().polish(self.fav_btn)

    def _on_fav(self):
        if not self.current:
            return
        d = self.current.get("dialect", "")
        if store.is_favorite(d):
            store.remove_favorite(d)
        else:
            store.add_favorite(self.current)
        self._refresh_fav_btn()
        self.historyChanged.emit()

    def _on_speak(self):
        if not self.current:
            QMessageBox.information(self, "提示", "请先解析一句方言再朗读。")
            return
        mode = self.speak_mode.currentData()
        txt = self.current.get("mandarin" if mode == "mandarin" else "dialect", "")
        if not txt or txt == "—":
            QMessageBox.information(self, "提示", "没有可朗读的内容。")
            return
        self.speak_btn.setEnabled(False)
        self.info.setText("🎙 语音合成中…（在线 TTS）")
        self._tts_worker = run_worker(backend.tts_synthesize, txt, mode,
                                      on_finished=self._on_spoken,
                                      on_error=self._on_speak_error)

    def _on_spoken(self, path):
        self.speak_btn.setEnabled(True)
        self.info.setText("")
        if path and os.path.exists(path) and self._player is not None:
            try:
                self._player.setSource(QUrl.fromLocalFile(path))
                self._player.play()
                return
            except Exception:
                pass
        self._fallback_speak()

    def _on_speak_error(self, msg):
        self.speak_btn.setEnabled(True)
        self.info.setText("")
        self._fallback_speak()

    def _fallback_speak(self):
        if self._tts is not None:
            try:
                mode = self.speak_mode.currentData()
                txt = self.current.get("mandarin" if mode == "mandarin" else "dialect", "")
                if txt and txt != "—":
                    self._tts.say(txt)
                    return
            except Exception:
                pass
        QMessageBox.information(self, "朗读不可用",
            "在线语音合成需要联网；当前环境也未提供系统语音引擎。")

    # ----------------------------- 录音 -----------------------------
    def _refresh_asr_mode(self):
        """根据 backend 当前生效的识别引擎，显示识别方式提示。"""
        eng = backend.resolve_asr_engine()
        if eng == "xunfei":
            self.asr_mode.setText("识别方式：云端讯飞（需联网，支持河南话方言）")
        elif eng == "offline_onnx":
            self.asr_mode.setText("识别方式：本地离线 · FunASR-ONNX（纯 CPU，零上传）")
        elif eng == "funasr":
            self.asr_mode.setText("识别方式：本地离线 · FunASR(torch)")
        else:
            self.asr_mode.setText("识别方式：未配置（录音将无法识别，详见 .env.example）")

    def _on_rec(self):
        if self.recorder.is_recording:
            self._stop_rec()
        else:
            self._start_rec()

    def _start_rec(self):
        try:
            self.recorder.start()
        except Exception as e:
            QMessageBox.warning(self, "无法录音", str(e))
            return
        self.rec_btn.setText("■ 停止录音")
        self.rec_btn.setProperty("recording", True)
        self.rec_btn.style().unpolish(self.rec_btn)
        self.rec_btn.style().polish(self.rec_btn)
        self.info.setText("正在录音…点击「停止录音」结束")
        self._timer.start(50)

    def _stop_rec(self):
        self._timer.stop()
        self.level.setValue(0)
        self.rec_btn.setText("🎙 录音识别")
        self.rec_btn.setProperty("recording", False)
        self.rec_btn.style().unpolish(self.rec_btn)
        self.rec_btn.style().polish(self.rec_btn)
        self.info.setText("识别中…")
        wav = self.recorder.stop()
        if not wav:
            self.info.setText("")
            QMessageBox.information(self, "提示", "没录到声音，请靠近麦克风重试。")
            return
        self._worker = run_worker(backend.transcribe_audio, wav, ".wav",
                                  on_finished=self._on_transcribed,
                                  on_error=lambda e: self._on_error(e))

    def _on_transcribed(self, res):
        text = (res.get("text") or "").strip()
        if not text:
            self.info.setText("")
            QMessageBox.information(self, "提示", "未识别出文字，请靠近麦克风重试。")
            return
        # 智能纠错：识别结果与词库词条高度相似但不一致时自动纠正
        corr = backend.correct_text(text)
        if corr["suggestion"] and corr["suggestion"] != text:
            QMessageBox.information(
                self, "🪄 智能纠错",
                f"识别结果已自动纠正：\n「{text}」 → 「{corr['suggestion']}」"
            )
            text = corr["suggestion"]
        self.input.setPlainText(text)
        src = res.get("source", "")
        if src == "xfyun":
            tag = "讯飞识别"
        elif src == "offline_onnx":
            tag = "本地离线识别（FunASR）"
        elif src == "offline_funasr":
            tag = "本地 FunASR"
        else:
            tag = "识别"
        self.info.setText("")
        self._on_parse_with_tag(tag)

    def _on_parse_with_tag(self, tag):
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.parse_btn.setEnabled(False)
        self.rec_btn.setEnabled(False)
        self.info.setText(tag + " · 解析中…")
        self._worker = run_worker(backend.process_text, text,
                                  on_finished=lambda r: self._on_parsed(r, tag),
                                  on_error=lambda e: self._on_error(e))

    def _update_level(self):
        if self.recorder.is_recording:
            self.level.setValue(int(self.recorder.get_level() * 100))
        else:
            self.level.setValue(0)

    # ----------------------------- 分享卡片 -----------------------------
    def _on_card(self):
        if not self.current:
            QMessageBox.information(self, "提示", "请先解析一句方言再生成卡片。")
            return
        dlg = CardDialog(self.current, self)
        dlg.exec()

    # ----------------------------- 我的词库（M2-3）-----------------------------
    def _refresh_examples(self):
        """示例下拉根据当前全部词库（含用户自定义）刷新。"""
        self.example.blockSignals(True)
        self.example.clear()
        self.example.addItem("— 选一句示例 —", "")
        for ex in backend.get_examples():
            self.example.addItem(f"{ex['dialect']}  →  {ex['mandarin']}", ex["dialect"])
        self.example.blockSignals(False)

    def _on_open_dict(self):
        dlg = CustomDictDialog(self)
        dlg.exec()
        self._refresh_examples()

    # ----------------------------- 换肤 -----------------------------
    def apply_theme(self):
        """主题切换时由 MainWindow 调用：重新套用内联样式（标题等已改 QSS objectName 自动换肤）。"""
        self.info.setStyleSheet(f"color:{theme.TXT_DIM};font-size:12px;")
        self.asr_mode.setStyleSheet(f"color:{theme.GREEN};font-size:12px;font-weight:600;")
        self.r_dialect.setStyleSheet(f"color:{theme.TITLE};font-size:18px;font-weight:700;")
        self.r_engine.setStyleSheet(f"color:{theme.TXT_DIM};font-size:12px;")
        for lab, val in getattr(self, "_sec_pairs", []):
            lab.setStyleSheet(f"color:{theme.GREEN};font-size:12px;font-weight:700;")
            val.setStyleSheet(f"color:{theme.TXT_DIM};font-size:15px;")


class CardDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("分享卡片")
        self.data = data
        self.pix = self._render()
        self._build()

    def _render(self):
        W, H = 640, 820
        pm = QPixmap(W, H)
        pm.fill(QColor(theme.BG))
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)

        # 边框
        p.setPen(QColor(theme.GREEN))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(18, 18, W - 36, H - 36, 16, 16)

        # 标题
        p.setPen(QColor(theme.TITLE))
        p.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        p.drawText(40, 70, "河南方言语音板")

        p.setPen(QColor(theme.GREEN))
        p.setFont(QFont("Microsoft YaHei", 12))
        p.drawText(40, 98, "HENAN DIALECT · 方言卡片")

        # 原句
        p.setPen(QColor(theme.GREEN))
        p.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        p.drawText(40, 150, "方言原句")
        p.setPen(QColor(theme.TITLE))
        p.setFont(QFont("Microsoft YaHei", 30, QFont.Bold))
        p.drawText(40, 192, self.data.get("dialect", ""))

        # 逐词拼音
        wp = self.data.get("word_pinyin") or ""
        if wp:
            p.setPen(QColor(theme.TXT_DIM))
            p.setFont(QFont("Microsoft YaHei", 14))
            p.drawText(40, 226, self._clip(wp, 46))

        # 普通话
        p.setPen(QColor(theme.GREEN))
        p.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        p.drawText(40, 280, "普通话")
        p.setPen(QColor(theme.TXT_DIM))
        p.setFont(QFont("Microsoft YaHei", 22))
        p.drawText(40, 316, self._clip(self.data.get("mandarin", ""), 22))

        # 整句拼音
        py = self.data.get("pinyin") or ""
        if py:
            p.setPen(QColor(theme.GREEN))
            p.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            p.drawText(40, 364, "拼音")
            p.setPen(QColor(theme.TXT_DIM))
            p.setFont(QFont("Microsoft YaHei", 16))
            p.drawText(40, 392, self._clip(py, 40))

        # 释义（自动换行）
        expl = self.data.get("explanation") or ""
        p.setPen(QColor(theme.GREEN))
        p.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        p.drawText(40, 450, "释义")
        p.setPen(QColor(theme.TXT_DIM))
        p.setFont(QFont("Microsoft YaHei", 15))
        self._wrap(p, expl, 40, 480, W - 80, 26)

        # 页脚
        p.setPen(QColor(theme.GREEN_DIM))
        p.setFont(QFont("Microsoft YaHei", 11))
        p.drawText(40, H - 40, "释义由 AI 或内置词库生成，仅供参考")
        p.end()
        return pm

    @staticmethod
    def _clip(s, n):
        s = str(s)
        return s if len(s) <= n else s[: n - 1] + "…"

    def _wrap(self, p, text, x, y, maxw, lh):
        text = str(text)
        line = ""
        for ch in text:
            if p.fontMetrics().horizontalAdvance(line + ch) > maxw and line:
                p.drawText(x, y, line)
                y += lh
                line = ch
            else:
                line += ch
        if line:
            p.drawText(x, y, line)

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12)
        from PySide6.QtWidgets import QLabel as _L
        lab = _L()
        lab.setPixmap(self.pix)
        v.addWidget(lab)
        row = QHBoxLayout()
        save = QPushButton("💾 保存图片")
        save.clicked.connect(self._save)
        row.addStretch(1)
        row.addWidget(save)
        v.addLayout(row)

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存卡片", "方言卡片.png", "PNG (*.png)")
        if path:
            self.pix.save(path, "PNG")
            QMessageBox.information(self, "已保存", f"卡片已保存到：\n{path}")


class CustomDictDialog(QDialog):
    """我的词库：列出自定义词（双击删除）、单条添加、从 JSON 批量导入。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("我的词库（自定义方言词）")
        self.resize(540, 560)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        v.addWidget(QLabel("已添加自定义词（双击某条可删除）："))
        self.list = QListWidget()
        self._fill()
        self.list.itemDoubleClicked.connect(self._del)
        v.addWidget(self.list)

        f = QFrame(objectName="panel")
        f.setFrameShape(QFrame.NoFrame)
        fl = QVBoxLayout(f)
        fl.setContentsMargins(12, 12, 12, 12)
        fl.setSpacing(8)
        self.in_d = QLineEdit()
        self.in_d.setPlaceholderText("方言词，如 中嘞")
        self.in_m = QLineEdit()
        self.in_m.setPlaceholderText("普通话释义，如 行啊/可以")
        self.in_c = QLineEdit("自定义")
        self.in_r = QLineEdit("通用")
        for w, lab in [(self.in_d, "方言词 *"), (self.in_m, "普通话释义 *"),
                       (self.in_c, "分类（可选）"), (self.in_r, "地市（可选，如 豫西）")]:
            fl.addWidget(QLabel(lab))
            fl.addWidget(w)
        add = QPushButton("➕ 添加这个词", objectName="primary")
        add.clicked.connect(self._add)
        fl.addWidget(add)
        v.addWidget(f)

        row = QHBoxLayout()
        imp = QPushButton("📥 从 JSON 导入")
        imp.clicked.connect(self._import)
        row.addStretch(1)
        row.addWidget(imp)
        v.addLayout(row)

    def _fill(self):
        self.list.clear()
        for p in backend.get_user_words():
            self.list.addItem(
                f"{p['dialect']}  →  {p['mandarin']}  ({p.get('region', '通用')})"
            )

    def _add(self):
        d = self.in_d.text().strip()
        m = self.in_m.text().strip()
        if not d or not m:
            QMessageBox.warning(self, "缺字段", "方言词与普通话释义都要填。")
            return
        try:
            backend.add_custom_word(
                d, m,
                category=self.in_c.text().strip() or "自定义",
                region=self.in_r.text().strip() or "通用",
            )
            self._fill()
            self.in_d.clear()
            self.in_m.clear()
        except Exception as e:
            QMessageBox.warning(self, "出错", str(e))

    def _del(self, item):
        d = item.text().split("  →  ")[0].strip()
        backend.remove_custom_word(d)
        self._fill()

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择词库 JSON", "", "JSON (*.json)")
        if not path:
            return
        try:
            n = backend.import_custom_dict(path)
            QMessageBox.information(self, "导入完成", f"成功导入 {n} 条自定义词。")
            self._fill()
        except Exception as e:
            QMessageBox.warning(self, "导入失败", str(e))
