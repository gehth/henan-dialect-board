#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""暗灰 + 翠绿「商业情报终端」风格 QSS 主题（支持 暗/亮 双主题 + 字号缩放/长辈模式）。

设计要点：
- 双调色板：dark（默认）/ light（新增）。所有颜色集中在 PALETTES，set_theme() 切换当前调色板
  并刷新模块级常量（BG/GREEN/TXT_DIM …）与 *_STYLE 字符串，使 `theme.X` 在运行时始终解析为当前主题色。
- build_qss(scale, theme)：生成可套用到整个 QApplication 的样式表；scale>1 即「长辈模式」。
- 页面若用 `import theme` 后引用 `theme.GREEN` 等，切换主题后调用 page.apply_theme() 即可实时换肤；
  用 objectName（QLabel#title/#sub/#section、QFrame#panel、QPushButton#nav …）的控件由 QSS 自动换肤。
"""

# ----------------------------- 调色板 -----------------------------
PALETTES = {
    "dark": dict(
        BG="#0b0f12", PANEL="#11171c", PANEL2="#0e1419", LINE="#1d2a30",
        GREEN="#2ee6a6", GREEN_DIM="#1c9e74", GREEN_GLOW="rgba(46,230,166,.16)",
        TXT="#cfe9e0", TXT_DIM="#7c9a90", WARN="#ffb454", BLUE="#7fd6ff",
        TITLE="#eafff7",
    ),
    "light": dict(
        BG="#eef1f4", PANEL="#ffffff", PANEL2="#e6eaee", LINE="#cfd6dd",
        GREEN="#0f9d6b", GREEN_DIM="#0b7d54", GREEN_GLOW="rgba(15,157,107,.16)",
        TXT="#1f2d2a", TXT_DIM="#5b6b66", WARN="#c47a00", BLUE="#1f7fa8",
        TITLE="#0b3d2e",
    ),
}

FONT = '"Cascadia Code","Consolas","Microsoft YaHei","PingFang SC",monospace'

# 当前主题（set_theme 时切换）
_THEME = "dark"

# 模块级常量（set_theme 时刷新，供 `theme.X` 实时取色）
BG = PALETTES["dark"]["BG"]
PANEL = PALETTES["dark"]["PANEL"]
PANEL2 = PALETTES["dark"]["PANEL2"]
LINE = PALETTES["dark"]["LINE"]
GREEN = PALETTES["dark"]["GREEN"]
GREEN_DIM = PALETTES["dark"]["GREEN_DIM"]
GREEN_GLOW = PALETTES["dark"]["GREEN_GLOW"]
TXT = PALETTES["dark"]["TXT"]
TXT_DIM = PALETTES["dark"]["TXT_DIM"]
WARN = PALETTES["dark"]["WARN"]
BLUE = PALETTES["dark"]["BLUE"]
TITLE = PALETTES["dark"]["TITLE"]


def palette(theme: str = None) -> dict:
    """返回指定（或当前）主题的调色板副本。"""
    name = theme if theme in PALETTES else _THEME
    return dict(PALETTES[name])


def set_theme(name: str = "dark"):
    """切换当前主题并刷新所有模块级颜色常量与 *_STYLE 字符串。"""
    global _THEME, BG, PANEL, PANEL2, LINE, GREEN, GREEN_DIM, GREEN_GLOW
    global TXT, TXT_DIM, WARN, BLUE, TITLE
    global TITLE_STYLE, SUB_STYLE, HEAD_LABEL_STYLE, GREEN_STYLE, DIM_STYLE, QSS
    _THEME = name if name in PALETTES else "dark"
    p = PALETTES[_THEME]
    BG, PANEL, PANEL2 = p["BG"], p["PANEL"], p["PANEL2"]
    LINE = p["LINE"]
    GREEN, GREEN_DIM, GREEN_GLOW = p["GREEN"], p["GREEN_DIM"], p["GREEN_GLOW"]
    TXT, TXT_DIM = p["TXT"], p["TXT_DIM"]
    WARN, BLUE, TITLE = p["WARN"], p["BLUE"], p["TITLE"]
    TITLE_STYLE = f"color:{TITLE};font-size:21px;font-weight:700;"
    SUB_STYLE = f"color:{TXT_DIM};font-size:12.5px;"
    HEAD_LABEL_STYLE = f"color:{GREEN};font-size:13px;font-weight:700;letter-spacing:1px;"
    GREEN_STYLE = f"color:{GREEN};"
    DIM_STYLE = f"color:{TXT_DIM};font-size:12px;"
    QSS = build_qss(1.0, _THEME)


def build_qss(scale: float = 1.0, theme: str = None) -> str:
    """生成 QSS。scale>1 即「长辈模式」：整体字号放大、对比度加强。

    theme=None 时使用当前全局主题（_THEME）。
    """
    eff = theme if theme in PALETTES else _THEME
    p = palette(eff)
    BG, PANEL, PANEL2, LINE = p["BG"], p["PANEL"], p["PANEL2"], p["LINE"]
    GREEN, GREEN_DIM, GREEN_GLOW = p["GREEN"], p["GREEN_DIM"], p["GREEN_GLOW"]
    TXT, TXT_DIM, WARN, BLUE, TITLE = p["TXT"], p["TXT_DIM"], p["WARN"], p["BLUE"], p["TITLE"]

    bs = int(round(14 * scale))

    def f(px):
        return int(round(px * scale))

    line_c = LINE if scale <= 1.0 else ("#2c4048" if eff == "dark" else "#9fb0bd")
    txt_c = TXT if scale <= 1.0 else ("#e6fff5" if eff == "dark" else "#0b3d2e")
    dim_c = TXT_DIM if scale <= 1.0 else ("#9fc4b8" if eff == "dark" else "#3f4f4a")
    return f"""
QWidget {{
    background-color: {BG};
    color: {txt_c};
    font-family: {FONT};
    font-size: {bs}px;
}}
QMainWindow, QDialog {{ background-color: {BG}; }}

QFrame#panel {{
    background-color: {PANEL};
    border: 1px solid {line_c};
    border-radius: {f(10)}px;
}}
QFrame#panel:hover {{
    border-color: {GREEN_DIM};
}}

QLabel#title {{ color: {TITLE}; font-size: {f(21)}px; font-weight: 700; }}
QLabel#sub {{ color: {dim_c}; font-size: {f(12.5)}px; }}
QLabel#section {{ color: {GREEN}; font-size: {f(13)}px; font-weight: 700; letter-spacing: 1px; }}
QLabel#hint {{ color: {dim_c}; font-size: {f(12)}px; }}

QPushButton {{
    background-color: {PANEL2};
    color: {txt_c};
    border: 1px solid {line_c};
    border-radius: {f(8)}px;
    padding: {f(8)}px {f(14)}px;
}}
QPushButton:hover {{ border-color: {GREEN_DIM}; color: {GREEN}; background-color: {PANEL}; }}
QPushButton:pressed {{ background-color: {GREEN_GLOW}; }}
QPushButton:disabled {{ color: {dim_c}; border-color: {line_c}; }}
QPushButton#primary {{
    background-color: {GREEN_DIM};
    color: #04130d;
    border: 1px solid {GREEN};
    font-weight: 700;
}}
QPushButton#primary:hover {{ background-color: {GREEN}; }}
QPushButton#nav {{
    background-color: transparent;
    border: none;
    border-left: {f(3)}px solid transparent;
    text-align: left;
    padding: {f(10)}px {f(14)}px;
    color: {dim_c};
    border-radius: 0;
}}
QPushButton#nav:hover {{ color: {GREEN}; background-color: {PANEL2}; }}
QPushButton#nav[active="true"] {{
    color: {GREEN};
    background-color: {PANEL};
    border-left: {f(3)}px solid {GREEN};
    font-weight: 700;
}}
QPushButton#rec[recording="true"] {{
    background-color: #c0392b;
    color: #fff;
    border: 1px solid #ff6b5b;
}}
QPushButton#fav[on="true"] {{
    background-color: {GREEN_GLOW};
    color: {GREEN};
    border: 1px solid {GREEN};
}}
QPushButton#elder {{
    border: 1px dashed {GREEN_DIM};
    color: {GREEN};
}}

QLineEdit, QPlainTextEdit, QTextEdit, QComboBox {{
    background-color: {PANEL2};
    color: {txt_c};
    border: 1px solid {line_c};
    border-radius: {f(8)}px;
    padding: {f(8)}px {f(10)}px;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color: {GREEN_DIM}; }}
QPlainTextEdit#input {{ font-size: {f(16)}px; }}
QComboBox QAbstractItemView {{
    background-color: {PANEL};
    color: {txt_c};
    selection-background-color: {GREEN_DIM};
}}

QProgressBar {{
    background-color: {PANEL2};
    border: 1px solid {line_c};
    border-radius: {f(6)}px;
    text-align: center;
    color: {dim_c};
}}
QProgressBar::chunk {{ background-color: {GREEN}; border-radius: {f(5)}px; }}

QListWidget {{
    background-color: {PANEL2};
    border: 1px solid {line_c};
    border-radius: {f(8)}px;
    padding: {f(4)}px;
}}
QListWidget::item {{ padding: {f(8)}px; border-bottom: 1px solid {line_c}; }}
QListWidget::item:hover {{ background-color: {PANEL}; }}
QListWidget::item:selected {{ background-color: {GREEN_GLOW}; color: {GREEN}; }}

QScrollBar:vertical {{
    background: {PANEL2};
    width: {f(10)}px;
    border-radius: {f(5)}px;
}}
QScrollBar::handle:vertical {{
    background: {GREEN_DIM};
    border-radius: {f(5)}px;
}}
QScrollBar::handle:vertical:hover {{ background: {GREEN}; }}
QTabWidget::pane {{ border: 1px solid {line_c}; border-radius: {f(8)}px; }}
QTabBar::tab {{
    background: {PANEL2};
    color: {dim_c};
    padding: {f(8)}px {f(16)}px;
    border: 1px solid {line_c};
    border-bottom: none;
    border-top-left-radius: {f(8)}px;
    border-top-right-radius: {f(8)}px;
}}
QTabBar::tab:selected {{ background: {PANEL}; color: {GREEN}; border-color: {GREEN_DIM}; }}
QToolTip {{
    background-color: {PANEL};
    color: {txt_c};
    border: 1px solid {GREEN_DIM};
    padding: {f(4)}px;
}}
QGraphicsOpacityEffect {{ }}
"""


# 初始化当前主题常量与兼容旧调用的样式字符串
set_theme("dark")
