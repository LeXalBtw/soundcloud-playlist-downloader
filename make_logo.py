"""Génère le logo (assets/logo.png, icon.ico, icon.icns). Lancer : python make_logo.py"""
import os
from PIL import Image, ImageDraw

SIZE = 1024
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(OUT, exist_ok=True)


def make():
    S = 4  # supersampling pour des bords lisses
    n = SIZE * S
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))

    # Dégradé orange SoundCloud (haut clair -> bas foncé)
    grad = Image.new("RGBA", (n, n))
    gp = grad.load()
    top, bot = (255, 138, 0), (255, 60, 0)
    for y in range(n):
        t = y / (n - 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,)
        for x in range(n):
            gp[x, y] = c

    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, n - 1, n - 1), radius=int(n * 0.23), fill=255)
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    # Barres de son façon égaliseur, centrées
    heights = [0.20, 0.38, 0.56, 0.74, 0.50, 0.66, 0.34, 0.18]
    bar_w = n * 0.075
    gap = n * 0.032
    total = len(heights) * bar_w + (len(heights) - 1) * gap
    x0 = (n - total) / 2
    cy = n / 2
    for i, h in enumerate(heights):
        x = x0 + i * (bar_w + gap)
        hh = n * h
        d.rounded_rectangle((x, cy - hh / 2, x + bar_w, cy + hh / 2), radius=bar_w / 2, fill=(255, 255, 255, 255))

    return img.resize((SIZE, SIZE), Image.LANCZOS)


if __name__ == "__main__":
    logo = make()
    logo.save(os.path.join(OUT, "logo.png"))
    logo.save(os.path.join(OUT, "icon.ico"), sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    logo.save(os.path.join(OUT, "icon.icns"))
    print("Logo généré dans", OUT)
