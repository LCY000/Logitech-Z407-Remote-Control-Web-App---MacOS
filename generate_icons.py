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

GOLD = (242, 184, 75, 255)
BLACK = (0, 0, 0, 255)
TRANSPARENT = (0, 0, 0, 0)


def draw_waveform(size: int, fg: tuple) -> Image.Image:
    """Five rounded bars, tallest in centre, on a transparent background."""
    img = Image.new("RGBA", (size, size), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    bars = 5
    heights = [0.30, 0.65, 1.00, 0.65, 0.30]
    margin = size * 0.10
    usable = size - 2 * margin
    slot = usable / bars
    bar_w = slot * 0.65
    gap = slot - bar_w
    radius = max(1, int(bar_w * 0.45))
    max_bar_h = (size - margin * 2) * 0.88

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

    # --- Menu bar icons (monochrome template image) ---
    save_png(draw_waveform(18, BLACK),  "assets/icon_menubar.png")
    save_png(draw_waveform(36, BLACK),  "assets/icon_menubar@2x.png")

    # --- Web icons ---
    save_png(draw_waveform(192, GOLD),  "static/icon_192.png")
    save_png(draw_waveform(512, GOLD),  "static/icon_512.png")

    # --- Favicon (16 + 32 px embedded in one .ico) ---
    icon16 = draw_waveform(16, GOLD)
    icon32 = draw_waveform(32, GOLD)
    icon16.save("static/favicon.ico", format="ICO",
                sizes=[(16, 16), (32, 32)], append_images=[icon32])
    print("  wrote static/favicon.ico")

    # --- macOS .icns via iconutil ---
    iconset = "assets/icon.iconset"
    if os.path.exists(iconset):
        shutil.rmtree(iconset)
    os.makedirs(iconset)

    for base_size in [16, 32, 128, 256, 512]:
        save_png(draw_waveform(base_size,      GOLD), f"{iconset}/icon_{base_size}x{base_size}.png")
        save_png(draw_waveform(base_size * 2,  GOLD), f"{iconset}/icon_{base_size}x{base_size}@2x.png")

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
