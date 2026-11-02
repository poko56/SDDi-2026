from tkinter import filedialog

import customtkinter as ctk

from ui.pages.base import BasePage
from ui.theme import ACCENT_HOVER, ACCENT_PRIMARY, TEXT_MAIN, TEXT_MUTED, font
from ui.widgets import card


class DashboardPage(BasePage):
    title = "Dashboard"

    def build(self):
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 20))
        self._build_folder_card(top_row)

        self.app.on_folder_change(self._on_folder_changed)

    # ---------- Layout ----------

    def _build_folder_card(self, parent):
        folder = card(parent)
        folder.pack(side="right", fill="both", expand=True, padx=(10, 0))
        ctk.CTkLabel(folder, text="Target Folder", font=font(16, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(15, 5))
        self.lbl_folder = ctk.CTkLabel(folder, text="No folder selected", text_color=TEXT_MUTED,
                                       wraplength=360, justify="left")
        self.lbl_folder.pack(anchor="w", padx=20, pady=5)
        ctk.CTkButton(folder, text="Select Folder", command=self._select_folder, fg_color=ACCENT_PRIMARY,
                      hover_color=ACCENT_HOVER).pack(anchor="w", padx=20, pady=(5, 10))

    # ---------- Behaviour ----------

    def _select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.app.set_folder(folder)

    def _on_folder_changed(self, folder):
        self.lbl_folder.configure(text=folder)
