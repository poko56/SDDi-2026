from tkinter import filedialog

import customtkinter as ctk

from ui.pages.base import BasePage
from ui.theme import ACCENT_HOVER, ACCENT_PRIMARY, BG_HOVER, BG_SUBTLE, BORDER, TEXT_MAIN, TEXT_MUTED, font
from ui.widgets import card

APP_VERSION = "1.2.0"


class SettingsPage(BasePage):
    title = "Settings"

    def build(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._build_exclusions_card(scroll)
        self._build_about_card(scroll)

    def _section(self, parent, title, subtitle):
        box = card(parent)
        box.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(box, text=title, font=font(16, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(15, 2))
        ctk.CTkLabel(box, text=subtitle, font=font(12), text_color=TEXT_MUTED,
                     justify="left").pack(anchor="w", padx=20)
        return box

    @staticmethod
    def _small_button(parent, text, command, primary=False, **kwargs):
        style = ({"fg_color": ACCENT_PRIMARY, "hover_color": ACCENT_HOVER} if primary
                 else {"fg_color": BG_HOVER, "hover_color": BORDER, "text_color": TEXT_MAIN})
        return ctk.CTkButton(parent, text=text, command=command, height=34, **style, **kwargs)

    # ---------- Excluded folders ----------

    def _build_exclusions_card(self, parent):
        box = self._section(parent, "โฟลเดอร์ยกเว้น",
                            "Cleaner, การจัดไฟล์ และ Auto Monitor จะไม่แตะไฟล์ในโฟลเดอร์เหล่านี้")
        self.exclusion_list = ctk.CTkFrame(box, fg_color="transparent")
        self.exclusion_list.pack(fill="x", padx=20, pady=(10, 0))
        add_button = self._small_button(box, "+ เพิ่มโฟลเดอร์", self._add_exclusion, width=140)
        add_button.pack(anchor="w", padx=20, pady=(5, 15))
        self._render_exclusions()

    def _render_exclusions(self):
        for widget in self.exclusion_list.winfo_children():
            widget.destroy()
        folders = self.services.exclusion.folders
        if not folders:
            ctk.CTkLabel(self.exclusion_list, text="ยังไม่มีโฟลเดอร์ยกเว้น", text_color=TEXT_MUTED).pack(anchor="w")
        for folder in folders:
            row = ctk.CTkFrame(self.exclusion_list, fg_color=BG_SUBTLE, corner_radius=8)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=folder, text_color=TEXT_MAIN).pack(side="left", padx=10, pady=4)
            ctk.CTkButton(row, text="✕", width=28, height=28, fg_color="transparent", text_color="#EF4444",
                          hover_color=("#FEE2E2", "#7F1D1D"),
                          command=lambda f=folder: self._remove_exclusion(f)).pack(side="right", padx=4)

    def _add_exclusion(self):
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ที่ไม่ต้องการให้ ZipZap แตะ")
        if folder:
            folders = self.services.exclusion.folders
            if folder not in folders:
                self.services.set_excluded_folders(folders + [folder])
                self._render_exclusions()

    def _remove_exclusion(self, folder):
        self.services.set_excluded_folders([f for f in self.services.exclusion.folders if f != folder])
        self._render_exclusions()

    # ---------- About ----------

    def _build_about_card(self, parent):
        self._section(parent, "About ZipZap", f"Version {APP_VERSION}\nPython + CustomTkinter")
