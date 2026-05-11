"""
Run once from the project root to regenerate all icon assets.
Requires: Pillow, macOS iconutil (Xcode Command Line Tools)
Usage:   python generate_icons.py
"""
from __future__ import annotations
import os
import subprocess
import shutil
from PIL import Image, ImageDraw

GOLD  = (242, 184, 75, 255)
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
TRANSPARENT = (0, 0, 0, 0)
SITE_BG = (16, 24, 32, 255)   # #101820 — matches website dark background


def draw_waveform(size: int, fg: tuple,
                  heights: tuple = (0.40, 0.75, 1.00, 0.75, 0.40),
                  margin_ratio: float = 0.08, bar_ratio: float = 0.68,
                  bg: tuple = TRANSPARENT) -> Image.Image:
    """Five rounded waveform bars. bg=TRANSPARENT for icns/menu-bar; bg=SITE_BG for web icons."""
    bars = len(heights)
    img = Image.new("RGBA", (size, size), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    if bg != TRANSPARENT:
        corner = max(1, int(size * 0.20))
        draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=corner, fill=bg)

    margin = size * margin_ratio
    usable = size - 2 * margin
    slot = usable / bars
    bar_w = slot * bar_ratio
    gap = slot - bar_w
    radius = max(1, int(bar_w * 0.40))
    max_bar_h = (size - margin * 2) * 0.90

    for i, h in enumerate(heights):
        x0 = margin + i * slot + gap / 2
        x1 = x0 + bar_w
        bar_h = max_bar_h * h
        y0 = (size - bar_h) / 2
        y1 = y0 + bar_h
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fg)

    return img


def save_png(img: Image.Image, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.save(path, format="PNG")
    print(f"  wrote {path}")


def generate_svg_favicon(path: str,
                         fg: str = "#ffffff",
                         bg: str = "#101820",
                         heights: tuple = (0.40, 0.75, 1.00, 0.75, 0.40),
                         size: int = 100,
                         margin_ratio: float = 0.08,
                         bar_ratio: float = 0.68) -> None:
    bars = len(heights)
    margin = size * margin_ratio
    usable = size - 2 * margin
    slot = usable / bars
    bar_w = slot * bar_ratio
    gap = slot - bar_w
    bar_radius = max(1, bar_w * 0.40)
    max_bar_h = (size - margin * 2) * 0.90
    bg_radius = size * 0.20

    rects = []
    for i, h in enumerate(heights):
        x = margin + i * slot + gap / 2
        bar_h = max_bar_h * h
        y = (size - bar_h) / 2
        rects.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{bar_h:.2f}" '
            f'rx="{bar_radius:.2f}" fill="{fg}"/>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">'
        f'<rect width="{size}" height="{size}" rx="{bg_radius:.2f}" fill="{bg}"/>'
        + "".join(rects)
        + "</svg>"
    )

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(svg)
    print(f"  wrote {path}")


def main() -> None:
    os.makedirs("assets", exist_ok=True)
    os.makedirs("static", exist_ok=True)

    # --- Menu bar icon (high-res so Finder preview matches the app icon;
    #     app.py sets NSImage size to 18pt so macOS uses this as the menu bar source) ---
    save_png(draw_waveform(512, BLACK), "assets/icon_menubar.png")
    save_png(draw_waveform(512, BLACK), "assets/icon_menubar@2x.png")

    # --- Web icons (dark background + white bars, visible in all browser themes) ---
    save_png(draw_waveform(192, WHITE, bg=SITE_BG), "static/icon_192.png")
    save_png(draw_waveform(512, WHITE, bg=SITE_BG), "static/icon_512.png")

    # --- Favicon: SVG (crisp at all sizes) + ICO fallback for old browsers ---
    generate_svg_favicon("static/favicon.svg")
    icon32 = draw_waveform(32, WHITE, bg=SITE_BG)
    icon64 = draw_waveform(64, WHITE, bg=SITE_BG)
    icon32.save("static/favicon.ico", format="ICO",
                sizes=[(32, 32), (64, 64)], append_images=[icon64])
    print("  wrote static/favicon.ico")

    # --- macOS .icns (dark background + white bars, same style as favicon) ---
    iconset = "assets/icon.iconset"
    if os.path.exists(iconset):
        shutil.rmtree(iconset)
    os.makedirs(iconset)

    for base_size in [16, 32, 128, 256, 512]:
        save_png(draw_waveform(base_size,     WHITE, bg=SITE_BG), f"{iconset}/icon_{base_size}x{base_size}.png")
        save_png(draw_waveform(base_size * 2, WHITE, bg=SITE_BG), f"{iconset}/icon_{base_size}x{base_size}@2x.png")

    result = subprocess.run(
        ["iconutil", "-c", "icns", iconset, "-o", "assets/icon_app.icns"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  iconutil failed: {result.stderr}")
    else:
        print("  wrote assets/icon_app.icns")
        shutil.rmtree(iconset)

    print("Done.")


if __name__ == "__main__":
    main()
