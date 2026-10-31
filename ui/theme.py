"""Colours, fonts and icon helpers shared by every page. Tuples are (light, dark)."""
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

from core.paths import resource_path

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


def create_icon_image(icon_char, color, size=24):
    """Render a Material Icons glyph as a crisp CTkImage (drawn at 3x, then downscaled)."""
    scale = 3
    img_size = size * scale
    img = Image.new("RGBA", (img_size, img_size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    try:
        glyph_font = ImageFont.truetype(resource_path("assets", "MaterialIcons.ttf"), int(img_size * 0.9))
        bbox = draw.textbbox((0, 0), icon_char, font=glyph_font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((img_size - w) / 2 - bbox[0], (img_size - h) / 2 - bbox[1]), icon_char,
                  fill=resolve_color(color), font=glyph_font)
    except OSError:
        pass  # Missing font: show an empty icon rather than crash
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=img, size=(size, size))


class Icons:
    DASHBOARD = ""
    CLEANER = ""
    CONVERTER = ""
    AI = ""
    MONITOR = ""
    SETTINGS = ""
    DELETE = ""
    DUPLICATE = ""
    FOLDER = ""
    EDIT = ""
    DOCUMENT = ""
    IMAGE = ""
    AUDIO = ""
    SEND = ""
    PERSON = ""
    SPARKLE = ""
    SORT = ""
    CALENDAR = ""
    UNDO = ""
