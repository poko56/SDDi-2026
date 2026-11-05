import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.cleaner import ScanOptions
from core.file_types import format_size
from ui.pages.base import BasePage
from ui.theme import (ACCENT_HOVER, ACCENT_PRIMARY, BG_HOVER, BG_SUBTLE, BORDER, TEXT_MAIN, TEXT_MUTED,
                      Icons, create_icon_image, font)
from ui.widgets import card

MAX_ROWS_PER_GROUP = 30
GROUPS = [
    ("junk", "Temporary Files", Icons.DELETE),
    ("duplicate", "Duplicate Files", Icons.DUPLICATE),
    ("large", "Large & Unused", Icons.FOLDER),
]


class CleanerPage(BasePage):
    title = "Smart Cleaner"

    def build(self):
        self.scan_folder = ""
        # (BooleanVar, [ScanResult]) per visible row, plus one per group for rows not rendered
        self.selection = []

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_options_card()
        self._build_results_card()
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

        self.btn_scan = ctk.CTkButton(opts, text="🔍 Scan Now", height=45, fg_color=ACCENT_PRIMARY,
                                      hover_color=ACCENT_HOVER, font=font(14, "bold"), command=self._scan)
        self.btn_scan.pack(side="bottom", fill="x", padx=20, pady=20)

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

    def _build_results_card(self):
        results = card(self)
        results.grid(row=0, column=1, sticky="nsew")

        header = ctk.CTkFrame(results, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(header, text="ผลการสแกน", font=font(16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        self.lbl_summary = ctk.CTkLabel(header, text="ยังไม่ได้สแกน", text_color=TEXT_MUTED)
        self.lbl_summary.pack(side="right")

        self.results_frame = ctk.CTkScrollableFrame(results, fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=5)

    # ---------- Behaviour ----------

    def _on_folder_changed(self, folder):
        self.entry_folder.delete(0, "end")
        self.entry_folder.insert(0, folder)

    def _browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.app.set_folder(folder)

    def _scan(self):
        folder = self.entry_folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Smart Cleaner", "โปรดเลือกโฟลเดอร์ที่ถูกต้องก่อนสแกน")
            return
        options = ScanOptions(duplicates=self.var_dup.get(), junk=self.var_junk.get(), large=self.var_large.get())
        self.scan_folder = folder
        self.btn_scan.configure(state="disabled", text="Scanning...")
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        def done(results):
            self.btn_scan.configure(state="normal", text="🔍 Scan Now")
            self._show_results(results)

        def failed(error):
            self.btn_scan.configure(state="normal", text="🔍 Scan Now")
            messagebox.showerror("Smart Cleaner", f"สแกนไม่สำเร็จ: {error}")

        self.app.run_background(lambda: self.services.cleaner.scan(folder, options), done, failed)

    def _show_results(self, results):
        self.selection = []
        total = sum(r.size for r in results)
        self.lbl_summary.configure(text=f"พบ {len(results)} ไฟล์ ขนาดรวม {format_size(total)}")
        if not results:
            ctk.CTkLabel(self.results_frame, text="ไม่พบไฟล์ขยะหรือไฟล์ซ้ำในโฟลเดอร์นี้ 🎉",
                         text_color=TEXT_MUTED).pack(pady=30)
        for key, title, icon in GROUPS:
            items = [r for r in results if r.type == key]
            if items:
                self._render_group(title, icon, items)

    def _render_group(self, title, icon, items):
        group = ctk.CTkFrame(self.results_frame, fg_color=BG_SUBTLE, corner_radius=8)
        group.pack(fill="x", pady=(0, 10))
        header = ctk.CTkFrame(group, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(header, image=create_icon_image(icon, TEXT_MUTED, 16), text="").pack(side="left")
        ctk.CTkLabel(header, text=f" {title} ({len(items)})", font=font(13, "bold"),
                     text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(header, text=format_size(sum(i.size for i in items)), font=font(13, "bold"),
                     text_color=ACCENT_PRIMARY).pack(side="right")

        for item in items[:MAX_ROWS_PER_GROUP]:
            label = os.path.relpath(item.path, self.scan_folder)
            if item.original:
                label += f"  (ซ้ำกับ {os.path.basename(item.original)})"
            self._result_row(group, label, item.size, [item])
        hidden = items[MAX_ROWS_PER_GROUP:]
        if hidden:
            self._result_row(group, f"... และอีก {len(hidden)} ไฟล์ (เลือกทั้งหมด)", sum(i.size for i in hidden),
                             hidden, muted=True)

    def _result_row(self, parent, text, size, items, muted=False):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=2)
        var = ctk.BooleanVar(value=True)
        self.selection.append((var, items))
        ctk.CTkCheckBox(row, text="", width=20, fg_color=ACCENT_PRIMARY, variable=var).pack(side="left")
        ctk.CTkLabel(row, text=text, text_color=TEXT_MUTED if muted else TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(row, text=format_size(size), text_color=TEXT_MUTED).pack(side="right")
