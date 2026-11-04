import os
import subprocess
import sys

import customtkinter as ctk
from PIL import Image, ImageDraw

from ui.theme import BG_CARD, CHART_EMPTY, resolve_color


def card(parent, **kwargs):
    kwargs.setdefault("fg_color", BG_CARD)
    kwargs.setdefault("corner_radius", 15)
    return ctk.CTkFrame(parent, **kwargs)


def bind_mousewheel(widget, canvas):
    """Let the wheel scroll `canvas` while the pointer is over `widget` or any of its children."""
    def on_wheel(event):
        delta = event.delta if sys.platform == "darwin" else event.delta / 120
        canvas.yview_scroll(int(-delta), "units")

    widget.bind("<MouseWheel>", on_wheel, add="+")
    widget.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"), add="+")
    widget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"), add="+")
    for child in widget.winfo_children():
        bind_mousewheel(child, canvas)


def render_donut(segments, size=150, thickness=18):
    """Draw a donut chart. `segments` is [(percent, colour), ...]; empty draws a grey ring."""
    scale = 4
    img_size = size * scale
    img = Image.new("RGBA", (img_size, img_size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    width = thickness * scale
    bbox = [width / 2, width / 2, img_size - width / 2, img_size - width / 2]

    start = -90
    for percent, color in segments or [(100, CHART_EMPTY)]:
        if percent <= 0:
            continue
        end = start + percent * 3.6
        draw.arc(bbox, start=start, end=end, fill=resolve_color(color), width=int(width))
        start = end

    img = img.resize((size, size), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=img, size=(size, size))


def reveal_in_file_manager(path):
    """Show the file selected in Finder / Explorer (or open its folder on Linux)."""
    if sys.platform.startswith("win"):
        subprocess.run(["explorer", "/select,", os.path.normpath(path)], check=False)
    elif sys.platform == "darwin":
        subprocess.run(["open", "-R", path], check=False)
    else:
        subprocess.run(["xdg-open", os.path.dirname(path)], check=False)
