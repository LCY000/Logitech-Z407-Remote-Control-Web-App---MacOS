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


def draw_waveform(size: int, fg: tuple,
                  heights: tuple = (0.40, 0.75, 1.00, 0.75, 0.40),
                  margin_ratio: float = 0.08, bar_ratio: float = 0.68) -> Image.Image:
    """Five rounded waveform bars on a transparent background."""
    bars = len(heights)
    img = Image.new("RGBA", (size, size), TRANSPARENT)
    draw = ImageDraw.Draw(img)

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


def main() -> None:
    os.makedirs("assets", exist_ok=True)
    os.makedirs("static", exist_ok=True)

    # --- Menu bar icons (black template image — macOS renders white on dark menu bar) ---
    save_png(draw_waveform(18, BLACK), "assets/icon_menubar.png")
    save_png(draw_waveform(36, BLACK), "assets/icon_menubar@2x.png")

    # --- Web icons (white, matches menu bar style) ---
    save_png(draw_waveform(192, WHITE), "static/icon_192.png")
    save_png(draw_waveform(512, WHITE), "static/icon_512.png")

    # --- Favicon (white, 16 + 32 px embedded in one .ico) ---
    icon16 = draw_waveform(16, WHITE)
    icon32 = draw_waveform(32, WHITE)
    icon16.save("static/favicon.ico", format="ICO",
                sizes=[(16, 16), (32, 32)], append_images=[icon32])
    print("  wrote static/favicon.ico")

    # --- macOS .icns (white bars — visible against macOS grey rounded-square background) ---
    iconset = "assets/icon.iconset"
    if os.path.exists(iconset):
        shutil.rmtree(iconset)
    os.makedirs(iconset)

    for base_size in [16, 32, 128, 256, 512]:
        save_png(draw_waveform(base_size,     WHITE), f"{iconset}/icon_{base_size}x{base_size}.png")
        save_png(draw_waveform(base_size * 2, WHITE), f"{iconset}/icon_{base_size}x{base_size}@2x.png")

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
