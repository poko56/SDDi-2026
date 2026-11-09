import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.file_types import format_size
from core.organizer import ByFileType, ByModifiedMonth
from ui.pages.base import BasePage
from ui.theme import (ACCENT_HOVER, ACCENT_PRIMARY, BG_CARD, BG_HOVER, BG_SUBTLE, CHART_DOCUMENTS, CHART_EMPTY,
                      CHART_MEDIA, CHART_OTHERS, TEXT_MAIN, TEXT_MUTED, Icons, create_icon_image, font)
from ui.widgets import card, render_donut

RENAME_FILETYPES = [("Supported files", "*.jpg *.jpeg *.png *.webp *.heic *.pdf *.txt"), ("All files", "*.*")]


class DashboardPage(BasePage):
    title = "Dashboard"

    def build(self):
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 20))
        self._build_storage_card(top_row)
        self._build_folder_card(top_row)
        self._build_quick_actions()
        self._build_activity_log()

        self.app.on_folder_change(self._on_folder_changed)
        self.app.on_log(self._append_log)
        self._draw_donut(None, 0)

    # ---------- Layout ----------

    def _build_storage_card(self, parent):
        storage = card(parent)
        storage.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(storage, text="Storage Overview", font=font(16, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(15, 0))

        self.lbl_donut = ctk.CTkLabel(storage, text="")
        self.lbl_donut.pack(side="left", padx=20, pady=15)

        legend = ctk.CTkFrame(storage, fg_color="transparent")
        legend.pack(side="left", padx=10, pady=20, fill="y")
        self.lbl_docs = self._legend_row(legend, CHART_DOCUMENTS, "เอกสาร (0 B)")
        self.lbl_media = self._legend_row(legend, CHART_MEDIA, "มัลติมีเดีย (0 B)")
        self.lbl_others = self._legend_row(legend, CHART_OTHERS, "อื่นๆ (0 B)")
        self.lbl_free = self._legend_row(legend, CHART_EMPTY, "พื้นที่ว่างบนดิสก์")

    @staticmethod
    def _legend_row(parent, color, text):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(anchor="w", pady=4)
        ctk.CTkFrame(row, width=12, height=12, fg_color=color, corner_radius=6).pack(side="left", padx=(0, 10))
        label = ctk.CTkLabel(row, text=text, text_color=TEXT_MUTED, font=font(13))
        label.pack(side="left")
        return label

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

        actions = ctk.CTkFrame(folder, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 15))
        small = {"height": 30, "fg_color": BG_SUBTLE, "hover_color": BG_HOVER, "text_color": TEXT_MAIN,
                 "font": font(12, "bold")}
        self.btn_sort_type = ctk.CTkButton(
            actions, text=" จัดตามประเภท", image=create_icon_image(Icons.SORT, ACCENT_PRIMARY, 16),
            command=lambda: self._organize(ByFileType()), state="disabled", **small)
        self.btn_sort_type.pack(side="left", padx=(0, 6))
        self.btn_sort_month = ctk.CTkButton(
            actions, text=" จัดตามเดือน", image=create_icon_image(Icons.CALENDAR, ACCENT_PRIMARY, 16),
            command=lambda: self._organize(ByModifiedMonth()), state="disabled", **small)
        self.btn_sort_month.pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text=" ย้อนกลับ", image=create_icon_image(Icons.UNDO, TEXT_MUTED, 16),
                      command=self._undo, width=90, **small).pack(side="left")

    def _build_quick_actions(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(10, 20))
        ctk.CTkLabel(row, text="Quick Actions", font=font(16, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 10))
        buttons = ctk.CTkFrame(row, fg_color="transparent")
        buttons.pack(fill="x")

        def quick_button(text, command, icon, color):
            btn = ctk.CTkButton(buttons, text=f"  {text}", image=create_icon_image(icon, color, size=28),
                                command=command, fg_color=BG_CARD, text_color=TEXT_MAIN, hover_color=BG_SUBTLE,
                                height=80, corner_radius=15, font=font(14, "bold"))
            btn.pack(side="left", fill="x", expand=True, padx=5)
            return btn

        quick_button("ทำความสะอาด", lambda: self.app.show_page("cleaner"), Icons.DELETE, "#10B981")
        quick_button("แปลงไฟล์", lambda: self.app.show_page("converter"), Icons.CONVERTER, "#7C3AED")
        quick_button("AI วิเคราะห์", lambda: self.app.show_page("ai"), Icons.AI, "#F472B6")
        quick_button("เฝ้าระวัง", lambda: self.app.show_page("monitor"), Icons.MONITOR, "#F59E0B")
        self.btn_smart_rename = quick_button("Smart Rename", self._smart_rename, Icons.EDIT, "#3B82F6")

    def _build_activity_log(self):
        log_card = card(self)
        log_card.pack(fill="both", expand=True, pady=10)
        ctk.CTkLabel(log_card, text="Recent Activities", font=font(16, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(15, 10))
        self.txt_log = ctk.CTkTextbox(log_card, fg_color="transparent", text_color=TEXT_MUTED)
        self.txt_log.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # ---------- Behaviour ----------

    def on_show(self):
        self.refresh_stats()

    def _append_log(self, line):
        self.txt_log.insert("end", line)
        self.txt_log.see("end")

    def _select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.app.set_folder(folder)

    def _on_folder_changed(self, folder):
        self.lbl_folder.configure(text=folder)
        self.btn_sort_type.configure(state="normal")
        self.btn_sort_month.configure(state="normal")
        self.refresh_stats()

    def refresh_stats(self):
        folder = self.app.current_folder
        if not folder:
            self._draw_donut(None, 0)
            return
        self.lbl_donut.configure(text="Loading...", image="")
        self.app.run_background(lambda: self.services.analyzer.analyze(folder), self._show_stats,
                                lambda e: self.lbl_donut.configure(text="Error"))

    def _show_stats(self, stats):
        self.lbl_docs.configure(text=f"เอกสาร ({format_size(stats.documents_bytes)})")
        self.lbl_media.configure(text=f"มัลติมีเดีย ({format_size(stats.media_bytes)})")
        self.lbl_others.configure(text=f"อื่นๆ ({format_size(stats.other_bytes)})")
        self.lbl_free.configure(text=f"พื้นที่ว่างบนดิสก์ ({format_size(stats.disk_free_bytes)})")
        total = stats.total_bytes
        segments = None
        if total:
            segments = [(stats.documents_bytes / total * 100, CHART_DOCUMENTS),
                        (stats.media_bytes / total * 100, CHART_MEDIA),
                        (stats.other_bytes / total * 100, CHART_OTHERS)]
        self._draw_donut(segments, total)

    def _draw_donut(self, segments, total_bytes):
        image = render_donut(segments)
        center = f"{format_size(total_bytes) if total_bytes else '0 B'}\nUSED"
        self.lbl_donut.configure(image=image, text=center, text_color=ACCENT_PRIMARY, compound="center",
                                 font=font(18, "bold"))
        self.lbl_donut.image = image

    def _organize(self, strategy):
        folder = self.app.current_folder
        self.app.log(f"⏳ กำลังจัดไฟล์ตาม{strategy.label}...")

        def done(result):
            ok, message = result
            self.app.log(("✅ " if ok else "❌ ") + message)
            self.refresh_stats()

        self.app.run_background(lambda: self.services.organizer.organize_folder(folder, strategy), done)

    def _undo(self):
        ok, message = self.services.logger.undo_last_action()
        self.app.log(("↩️ " if ok else "⚠️ ") + message)
        if ok:
            self.refresh_stats()

    def _smart_rename(self):
        if not self.services.llm.is_configured:
            messagebox.showwarning("Smart Rename", "กรุณาตั้งค่า AI ในหน้า Settings ก่อนใช้งานครับ\n"
                                                   "(ใส่ Gemini API Key หรือเลือกโมเดล Local AI)")
            self.app.show_page("settings")
            return
        files = filedialog.askopenfilenames(filetypes=RENAME_FILETYPES)
        if not files:
            return
        self.btn_smart_rename.configure(state="disabled", text="  กำลังเปลี่ยนชื่อ...")

        def rename_all():
            renamed = 0
            for path in files:
                name = os.path.basename(path)
                self.app.log(f"⏳ กำลังให้ AI วิเคราะห์ไฟล์: {name}...")
                ok, message = self.services.organizer.smart_rename(path)
                if ok:
                    renamed += 1
                    self.app.log(f"✅ {name} → {message}")
                else:
                    self.app.log(f"⚠️ ข้ามไฟล์ {name}: {message}")
            return renamed

        def done(renamed):
            self.app.log(f"🎉 Smart Rename เสร็จสิ้น! เปลี่ยนไปได้ {renamed}/{len(files)} ไฟล์")
            self.btn_smart_rename.configure(state="normal", text="  Smart Rename")
            messagebox.showinfo("Smart Rename", f"เปลี่ยนชื่อสำเร็จ {renamed} จาก {len(files)} ไฟล์\n"
                                                "ดูรายละเอียดได้ใน Recent Activities")
            self.refresh_stats()

        self.app.run_background(rename_all, done)
