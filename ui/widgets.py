import sys

import customtkinter as ctk

from ui.theme import BG_CARD


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
