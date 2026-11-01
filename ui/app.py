import os
import tkinter as tk

import customtkinter as ctk
from PIL import Image

from core.paths import resource_path
from ui.theme import ACCENT_PRIMARY, ACCENT_SOFT, BG_CARD, BG_MAIN, SIDEBAR_BG, TEXT_MAIN, TEXT_MUTED, create_icon_image, font

PREFERRED_SIZE = (1200, 800)
MIN_SIZE = (960, 600)
SCREEN_MARGIN = (40, 100)  # Leave room for the menu bar, dock or taskbar


class ZipZapApp(ctk.CTk):
    """Main window: sidebar navigation, shared state and the bridge between worker threads and Tk.

    Pages never talk to each other directly. They read `current_folder`, and
    subscribe to folder changes and log messages (Observer pattern), so a page
    can be added or removed without touching the others.
    """

    PAGES = []

    def __init__(self, services):
        super().__init__()
        self.services = services

        ctk.set_appearance_mode(services.config.get("theme"))
        self.title("ZipZap - Smart File Manager")
        self._fit_to_screen()
        self.configure(fg_color=BG_MAIN)
        self._set_window_icon()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self._build_sidebar()
        self._build_content_area()

    # ---------- Layout ----------

    def _fit_to_screen(self):
        """Open at the preferred size, shrunk to fit small screens such as a 1280x720 projector."""
        width = min(PREFERRED_SIZE[0], self.winfo_screenwidth() - SCREEN_MARGIN[0])
        height = min(PREFERRED_SIZE[1], self.winfo_screenheight() - SCREEN_MARGIN[1])
        width, height = max(width, MIN_SIZE[0]), max(height, MIN_SIZE[1])
        x = max((self.winfo_screenwidth() - width) // 2, 0)
        y = max((self.winfo_screenheight() - height) // 3, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(*MIN_SIZE)
        self.resizable(True, True)

    def _set_window_icon(self):
        try:
            if os.name == "nt":
                self.iconbitmap(resource_path("icon.ico"))
            else:
                self._icon = tk.PhotoImage(file=resource_path("icon.png"))
                self.iconphoto(False, self._icon)
        except tk.TclError:
            pass

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=SIDEBAR_BG)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(len(self.PAGES) + 1, weight=1)

        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        try:
            logo = Image.open(resource_path("assets", "logo_transparent.png")).convert("RGBA")
            width = 180
            height = int(logo.height * width / logo.width)
            logo = logo.resize((width * 2, height * 2), Image.Resampling.LANCZOS)  # 2x for Retina
            self._logo = ctk.CTkImage(light_image=logo, size=(width, height))
            ctk.CTkLabel(logo_frame, image=self._logo, text="").pack(side="left")
        except OSError:
            ctk.CTkLabel(logo_frame, text="⚡ ZipZap", font=font(24, "bold"),
                         text_color=ACCENT_PRIMARY).pack(side="left")

        self._nav_buttons = {}
        for row, (key, label, icon, _) in enumerate(self.PAGES, start=1):
            btn = ctk.CTkButton(
                sidebar, text=f"  {label}", image=create_icon_image(icon, TEXT_MUTED),
                command=lambda k=key: self.show_page(k), fg_color="transparent", text_color=TEXT_MUTED,
                hover_color=BG_MAIN, font=font(14, "bold"), anchor="w", height=45,
            )
            btn.grid(row=row, column=0, padx=15, pady=5, sticky="ew")
            btn.icons = (create_icon_image(icon, ACCENT_PRIMARY), create_icon_image(icon, TEXT_MUTED))
            self._nav_buttons[key] = btn

    def _build_content_area(self):
        main = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")

        topbar = ctk.CTkFrame(main, height=60, fg_color=BG_CARD, corner_radius=0)
        topbar.pack(fill="x")
        self.lbl_page_title = ctk.CTkLabel(topbar, text="", font=font(20, "bold"), text_color=TEXT_MAIN)
        self.lbl_page_title.pack(side="left", padx=30, pady=15)

        container = ctk.CTkFrame(main, fg_color="transparent")
        container.pack(fill="both", expand=True)
        self.pages = {key: page_cls(container, self) for key, _, _, page_cls in self.PAGES}

    def show_page(self, key):
        for page_key, btn in self._nav_buttons.items():
            active = page_key == key
            btn.configure(
                fg_color=ACCENT_SOFT if active else "transparent",
                text_color=ACCENT_PRIMARY if active else TEXT_MUTED,
                image=btn.icons[0] if active else btn.icons[1],
            )
        for page in self.pages.values():
            page.pack_forget()
        page = self.pages[key]
        self.lbl_page_title.configure(text=page.title)
        page.pack(fill="both", expand=True, padx=30, pady=20)
        page.on_show()
