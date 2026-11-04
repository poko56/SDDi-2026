from tkinter import filedialog

import customtkinter as ctk

from ui.pages.base import BasePage
from ui.theme import (ACCENT_PRIMARY, BG_HOVER, BG_SUBTLE, BORDER, TEXT_MAIN, TEXT_MUTED, Icons,
                      create_icon_image, font)
from ui.widgets import card


class CleanerPage(BasePage):
    title = "Smart Cleaner"

    def build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_options_card()
        self.app.on_folder_change(self._on_folder_changed)

    def _build_options_card(self):
        opts = card(self, width=360)
        opts.grid(row=0, column=0, sticky="nsw", padx=(0, 15))
        opts.grid_propagate(False)

        ctk.CTkLabel(opts, text="Smart Cleaner", font=font(16, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(15, 2))
        ctk.CTkLabel(opts, text="หาไฟล์ขยะ ไฟล์ซ้ำ และไฟล์ใหญ่ที่ไม่ได้ใช้\nไฟล์ที่เลือกจะถูกย้ายไปถังขยะ ไม่ได้ลบทิ้ง",
                     text_color=TEXT_MUTED, justify="left", font=font(12)).pack(anchor="w", padx=20, pady=(0, 10))

        self.var_junk = ctk.BooleanVar(value=True)
        self.var_dup = ctk.BooleanVar(value=True)
        self.var_large = ctk.BooleanVar(value=False)
        self._option(opts, self.var_junk, "Temporary Files", "Cache, Log, ไฟล์ชั่วคราว", Icons.DELETE)
        self._option(opts, self.var_dup, "Duplicate Files", "ไฟล์เนื้อหาเหมือนกัน (SHA-256)", Icons.DUPLICATE)
        self._option(opts, self.var_large, "Large & Unused", "ใหญ่กว่า 50MB และไม่ได้แก้ไข 30 วัน", Icons.FOLDER)

        ctk.CTkLabel(opts, text="โฟลเดอร์เป้าหมาย", font=font(13, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(15, 5))
        self.entry_folder = ctk.CTkEntry(opts, text_color=TEXT_MAIN, fg_color=BG_SUBTLE)
        self.entry_folder.pack(fill="x", padx=20)
        ctk.CTkButton(opts, text="เลือกโฟลเดอร์", fg_color=BG_HOVER, text_color=TEXT_MAIN, hover_color=BORDER,
                      command=self._browse).pack(fill="x", padx=20, pady=8)

    @staticmethod
    def _option(parent, var, title, desc, icon):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=6)
        ctk.CTkCheckBox(row, text="", variable=var, width=24, fg_color=ACCENT_PRIMARY).pack(side="left")
        ctk.CTkLabel(row, image=create_icon_image(icon, TEXT_MUTED, 20), text="").pack(side="left", padx=8)
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.pack(side="left")
        ctk.CTkLabel(text, text=title, font=font(13, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(text, text=desc, font=font(11), text_color=TEXT_MUTED).pack(anchor="w")

    # ---------- Behaviour ----------

    def _on_folder_changed(self, folder):
        self.entry_folder.delete(0, "end")
        self.entry_folder.insert(0, folder)

    def _browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.app.set_folder(folder)
