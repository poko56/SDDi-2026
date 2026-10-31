"""Colours, fonts and icon helpers shared by every page. Tuples are (light, dark)."""
import customtkinter as ctk

BG_MAIN = ("#F3F5F9", "#0F172A")
BG_CARD = ("#FFFFFF", "#1E293B")
BG_SUBTLE = ("#F9FAFB", "#334155")
BG_HOVER = ("#F3F4F6", "#475569")
BORDER = ("#E5E7EB", "#475569")
TEXT_MAIN = ("#1F2937", "#F8FAFC")
TEXT_MUTED = ("#6B7280", "#94A3B8")
ACCENT_PRIMARY = ("#7C3AED", "#8B5CF6")
ACCENT_HOVER = ("#6D28D9", "#7C3AED")
ACCENT_SOFT = ("#EDE9FE", "#4C1D95")
ACCENT_SUCCESS = ("#10B981", "#34D399")
ACCENT_DANGER = ("#EF4444", "#F87171")
DANGER_HOVER = "#DC2626"
SIDEBAR_BG = ("#FFFFFF", "#1E293B")

CHART_DOCUMENTS = "#7C3AED"
CHART_MEDIA = "#10B981"
CHART_OTHERS = "#F472B6"
CHART_EMPTY = ("#E5E7EB", "#475569")

FONT_FAMILY = "Helvetica"


def font(size=13, weight="normal", slant="roman"):
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight, slant=slant)


def resolve_color(color):
    """PIL needs one colour; pick the light or dark half of a theme tuple."""
    if isinstance(color, tuple):
        return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
    return color
