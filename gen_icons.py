# -*- coding: utf-8 -*-
"""PWA 아이콘(icon-192.png, icon-512.png)을 생성하는 1회성 스크립트. (앱 실행 시에는 필요 없음)"""

from PIL import Image, ImageDraw, ImageFont

BG_COLOR = (37, 99, 235)  # --primary
TEXT_COLOR = (255, 255, 255)


def find_font(size):
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\malgunbd.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def make_icon(size, path):
    img = Image.new("RGB", (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font = find_font(int(size * 0.24))
    text = "ONDA"
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]), text, font=font, fill=TEXT_COLOR)

    img.save(path)
    print(f"saved {path}")


def make_favicon(path):
    img = Image.new("RGB", (256, 256), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = find_font(110)
    text = "O"
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((256 - w) / 2 - bbox[0], (256 - h) / 2 - bbox[1]), text, font=font, fill=TEXT_COLOR)
    img.save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(f"saved {path}")


if __name__ == "__main__":
    make_icon(192, "static/icons/icon-192.png")
    make_icon(512, "static/icons/icon-512.png")
    make_favicon("static/favicon.ico")
