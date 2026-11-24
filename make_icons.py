#!/usr/bin/env python3
"""Draw the home-screen bus icons (icon-192.png, icon-512.png). Needs Pillow.

Full-bleed background so Android can mask it to any shape; the bus stays
inside the central safe zone (a circle of 80 % of the width).
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BG, BODY, GLASS, DARK = "#80166F", "#FFFFFF", "#3A0A33", "#2A0725"
FONTS = ["/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def draw(size):
    S = 1024  # draw large, then downscale for smooth edges
    im = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(im)
    u = S / 100  # work in percent of the icon

    def box(x0, y0, x1, y1):
        return [round(x0 * u), round(y0 * u), round(x1 * u), round(y1 * u)]

    # wheels (behind the body), mirrors
    d.rounded_rectangle(box(32, 66, 42, 78), radius=2 * u, fill=DARK)
    d.rounded_rectangle(box(58, 66, 68, 78), radius=2 * u, fill=DARK)
    d.rounded_rectangle(box(23, 34, 28, 46), radius=1.5 * u, fill=BODY)
    d.rounded_rectangle(box(72, 34, 77, 46), radius=1.5 * u, fill=BODY)
    # body, front view
    d.rounded_rectangle(box(28, 22, 72, 72), radius=7 * u, fill=BODY)
    # destination sign with the line number
    d.rounded_rectangle(box(34, 26, 66, 35), radius=2 * u, fill=GLASS)
    font = next((ImageFont.truetype(f, round(8 * u)) for f in FONTS if os.path.exists(f)), None)
    if font:
        d.text((50 * u, 30.6 * u), "58", font=font, fill="#FFC94D", anchor="mm")
    # windscreen
    d.rounded_rectangle(box(32, 38, 68, 55), radius=3 * u, fill=GLASS)
    # headlights and grille
    d.ellipse(box(34, 60, 40, 66), fill="#FFC94D")
    d.ellipse(box(60, 60, 66, 66), fill="#FFC94D")
    d.rounded_rectangle(box(44, 61.5, 56, 64.5), radius=1 * u, fill=GLASS)
    return im.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    for n in (192, 512):
        draw(n).save(os.path.join(HERE, f"icon-{n}.png"), optimize=True)
        print("wrote", f"icon-{n}.png")
