import os
import tkinter as tk

import customtkinter as ctk

from core.paths import resource_path
from ui.theme import BG_MAIN

PREFERRED_SIZE = (1200, 800)
MIN_SIZE = (960, 600)
SCREEN_MARGIN = (40, 100)  # Leave room for the menu bar, dock or taskbar


class ZipZapApp(ctk.CTk):
    """Main window: sidebar navigation, shared state and the bridge between worker threads and Tk.

    Pages never talk to each other directly. They read `current_folder`, and
    subscribe to folder changes and log messages (Observer pattern), so a page
    can be added or removed without touching the others.
    """

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
