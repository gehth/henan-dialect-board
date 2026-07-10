"""生成扁平极简风格应用图标 app.ico（圆角绿块 + 白色话筒 + 声波）。

多尺寸 16/32/48/64/128/256，供 PyInstaller exe 图标与文档使用。
同时输出 app_preview.png（256 尺寸、白底）便于人工检查观感。
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "app.ico")
PREVIEW = os.path.join(ROOT, "app_preview.png")

GREEN = (15, 157, 107, 255)   # #0f9d6b 主题绿
WHITE = (255, 255, 255, 255)
WAVE = (255, 255, 255, 210)

SIZES = [16, 32, 48, 64, 128, 256]
images = []


def draw_icon(S: int) -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = max(1, round(S * 0.07))          # 外边距
    r = round(S * 0.22)                  # 圆角半径
    d.rounded_rectangle([m, m, S - m, S - m], radius=r, fill=GREEN)

    cx = S / 2.0
    head_w = S * 0.22
    head_h = S * 0.27
    head_top = S * 0.19
    head_bot = head_top + head_h

    # 话筒头（胶囊）
    d.rounded_rectangle([cx - head_w / 2, head_top, cx + head_w / 2, head_bot],
                        radius=head_w / 2, fill=WHITE)
    # 话筒杆
    stem_w = S * 0.06
    stem_top = head_bot - S * 0.01
    stem_bot = S * 0.55
    d.rounded_rectangle([cx - stem_w / 2, stem_top, cx + stem_w / 2, stem_bot],
                        radius=stem_w / 2, fill=WHITE)
    # 底座横线
    base_w = S * 0.30
    base_y = stem_bot + S * 0.03
    d.line([cx - base_w / 2, base_y, cx + base_w / 2, base_y],
           fill=WHITE, width=max(1, round(S * 0.045)))

    # 声波（中大型尺寸，左右对称两条同心弧）
    if S >= 48:
        cy_mid = (head_top + head_bot) / 2
        for i, k in enumerate((0.90, 1.35)):
            R = head_w * k
            box = [cx - R, cy_mid - R, cx + R, cy_mid + R]
            w = max(1, round(S * 0.022))
            d.arc(box, start=-65, end=65, fill=WAVE, width=w)     # 右侧声波弧 )))
    return img


for S in SIZES:
    images.append(draw_icon(S))

images[0].save(OUT, format="ICO", sizes=[(s, s) for s in SIZES],
               append_images=images[1:])
# 预览：256 尺寸贴白底
prev = Image.new("RGBA", (256, 256), (255, 255, 255, 255))
prev.paste(images[-1], (0, 0), images[-1])
prev.convert("RGB").save(PREVIEW)
print("已生成", OUT)
print("已生成预览", PREVIEW)
print("尺寸:", SIZES)
