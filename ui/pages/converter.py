import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.converter import SAME_AS_SOURCE
from core.file_types import format_size
from ui.pages.base import BasePage
from ui.theme import (ACCENT_HOVER, ACCENT_PRIMARY, ACCENT_SOFT, BG_CARD, BG_HOVER, BG_SUBTLE, BORDER, TEXT_MAIN,
                      TEXT_MUTED, Icons, create_icon_image, font)
from ui.widgets import card

SAME_FOLDER_LABEL = "โฟลเดอร์เดียวกับต้นฉบับ"
MODE_ICONS = {"Document": Icons.DOCUMENT, "Image": Icons.IMAGE, "Media": Icons.AUDIO}


class ConverterPage(BasePage):
    title = "Universal Converter"

    def build(self):
        converter = self.services.converter
        self.files = []
        self.mode = converter.modes()[0]
        self.var_target = ctk.StringVar(value=converter.targets_for(self.mode)[0])
        self.var_output = ctk.StringVar(value=SAME_FOLDER_LABEL)

        body = card(self)
        body.pack(fill="both", expand=True, pady=10)

        mode_row = ctk.CTkFrame(body, fg_color="transparent")
        mode_row.pack(fill="x", padx=20, pady=(20, 10))
        badge = ctk.CTkFrame(mode_row, fg_color=ACCENT_SOFT, corner_radius=10)
        badge.pack(side="right", padx=(10, 0))
        ctk.CTkLabel(badge, text="ALL-IN-ONE", text_color=ACCENT_PRIMARY, font=font(11, "bold")).pack(padx=10, pady=2)
        self.var_mode = ctk.StringVar(value=self.mode)
        ctk.CTkSegmentedButton(mode_row, values=converter.modes(), variable=self.var_mode,
                               command=self._on_mode_change).pack(side="left", fill="x", expand=True)

        # A single compact row, so the file list keeps its space on short screens
        drop_zone = ctk.CTkFrame(body, fg_color=BG_SUBTLE, corner_radius=10, border_width=2, border_color=BORDER)
        drop_zone.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(drop_zone, image=create_icon_image(Icons.DOCUMENT, ("#D1D5DB", "#64748B"), 32),
                     text="").pack(side="left", padx=(15, 10), pady=12)
        texts = ctk.CTkFrame(drop_zone, fg_color="transparent")
        texts.pack(side="left", pady=12)
        ctk.CTkLabel(texts, text="คลิก + Add Files เพื่อเพิ่มไฟล์ที่ต้องการแปลง", font=font(13, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(texts, text="รองรับ .docx, .jpg, .png, .heic, .mp4 ฯลฯ", text_color=TEXT_MUTED,
                     font=font(12)).pack(anchor="w")
        ctk.CTkButton(drop_zone, text="+ Add Files", fg_color="transparent", border_width=1, border_color=TEXT_MUTED,
                      text_color=TEXT_MAIN, hover_color=BG_HOVER, command=self._add_files).pack(side="right", padx=15)

        # Packed bottom-up so the file list in the middle takes the remaining space
        self.btn_start = ctk.CTkButton(body, text="🔄 เริ่มแปลงไฟล์", fg_color=ACCENT_PRIMARY, hover_color=ACCENT_HOVER,
                                       height=45, font=font(14, "bold"), command=self._convert, state="disabled")
        self.btn_start.pack(side="bottom", fill="x", padx=20, pady=(0, 20))

        controls = ctk.CTkFrame(body, fg_color="transparent")
        controls.pack(side="bottom", fill="x", padx=20, pady=(10, 15))
        target_col = ctk.CTkFrame(controls, fg_color="transparent")
        target_col.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkLabel(target_col, text="รูปแบบไฟล์ปลายทาง", text_color=TEXT_MUTED, font=font(12)).pack(anchor="w")
        self.menu_target = ctk.CTkOptionMenu(
            target_col, variable=self.var_target, values=converter.targets_for(self.mode),
            command=lambda _: self._refresh_list(), fg_color=BG_SUBTLE, text_color=TEXT_MAIN,
            button_color=BG_HOVER, button_hover_color=BORDER)
        self.menu_target.pack(fill="x", pady=(5, 0))

        output_col = ctk.CTkFrame(controls, fg_color="transparent")
        output_col.pack(side="left", fill="x", expand=True, padx=(10, 0))
        ctk.CTkLabel(output_col, text="บันทึกที่", text_color=TEXT_MUTED, font=font(12)).pack(anchor="w")
        output_row = ctk.CTkFrame(output_col, fg_color="transparent")
        output_row.pack(fill="x", pady=(5, 0))
        ctk.CTkEntry(output_row, textvariable=self.var_output, fg_color=BG_SUBTLE, text_color=TEXT_MAIN,
                     state="disabled").pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(output_row, text="เลือก", width=60, fg_color="transparent", border_width=1,
                      border_color=TEXT_MUTED, text_color=TEXT_MAIN, hover_color=BG_HOVER,
                      command=self._choose_output).pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(body, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=5)

    def _on_mode_change(self, mode):
        self.mode = mode
        self.files = []
        targets = self.services.converter.targets_for(mode)
        self.menu_target.configure(values=targets)
        self.var_target.set(targets[0])
        self._refresh_list()