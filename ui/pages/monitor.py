import os
from tkinter import messagebox

import customtkinter as ctk

from core.organizer import ByFileType
from core.watcher import CONVERT_FOLDER_NAME
from ui.pages.base import BasePage
from ui.theme import ACCENT_PRIMARY, BG_SUBTLE, TEXT_MAIN, TEXT_MUTED, font
from ui.widgets import card


class MonitorPage(BasePage):
    title = "Auto Monitor"

    def build(self):
        self.watched_folder = ""
        top = card(self)
        top.pack(fill="x", pady=10)
        ctk.CTkLabel(top, text="Auto Monitor (Watchdog)", font=font(18, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(top, text=("ไฟล์ใหม่ที่วางในโฟลเดอร์เป้าหมายจะถูกจัดเข้าโฟลเดอร์ตามประเภททันที\n"
                                f"ไฟล์ .docx ที่วางใน {CONVERT_FOLDER_NAME}/ จะถูกแปลงเป็น PDF อัตโนมัติ"),
                     text_color=TEXT_MUTED, justify="left").pack(anchor="w", padx=20, pady=(0, 15))
        self.switch = ctk.CTkSwitch(top, text="Enable Auto Monitor for Target Folder", progress_color=ACCENT_PRIMARY,
                                    command=self._toggle)
        self.switch.pack(anchor="w", padx=20, pady=(0, 20))

        log_card = card(self)
        log_card.pack(fill="both", expand=True, pady=10)
        ctk.CTkLabel(log_card, text="Activity Log", font=font(16, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(20, 10))
        self.txt_log = ctk.CTkTextbox(log_card, fg_color=BG_SUBTLE, text_color=TEXT_MAIN)
        self.txt_log.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.app.on_log(self._append_log)
        self.app.on_folder_change(self._on_folder_changed)

    def _append_log(self, line):
        self.txt_log.insert("end", line)
        self.txt_log.see("end")

    def _toggle(self):
        if self.switch.get() == 1:
            folder = self.app.current_folder
            if not folder:
                messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกโฟลเดอร์เป้าหมายที่หน้า Dashboard ก่อนเปิดระบบอัตโนมัติ")
                self.switch.deselect()
                return
            self._start(folder)
        else:
            self.services.watcher.stop_watching()
            self.app.log("🛑 หยุดเฝ้าระวังโฟลเดอร์")

    def _start(self, folder):
        callbacks = {"on_new_file": self._auto_sort, "on_pdf_convert": self._auto_pdf}
        ok, message = self.services.watcher.start_watching(folder, callbacks)
        if ok:
            self.watched_folder = folder
            self.app.log(f"✅ เริ่มเฝ้าระวังโฟลเดอร์: {folder}")
        else:
            self.switch.deselect()
            self.app.log(f"❌ {message}")

    def _on_folder_changed(self, folder):
        if self.services.watcher.is_running and folder != self.watched_folder:
            self._start(folder)

    # The two callbacks run on the watcher's thread, so they only touch thread-safe app methods

    def _auto_sort(self, path):
        try:
            new_path = self.services.organizer.organize_file(path, self.watched_folder, ByFileType())
        except OSError as e:
            self.app.log(f"❌ จัดหมวดหมู่ {os.path.basename(path)} ไม่สำเร็จ: {e}")
            return
        if new_path:
            rel = os.path.relpath(new_path, self.watched_folder)
            self.app.log(f"⚡ จัดหมวดหมู่อัตโนมัติ: {os.path.basename(path)} → {rel}")
            self.app.call_in_ui(self.app.pages["dashboard"].refresh_stats)

    def _auto_pdf(self, path):
        ok, result = self.services.converter.convert_docx_to_pdf(path)
        if ok:
            self.app.log(f"⚡ แปลง PDF อัตโนมัติ: {os.path.basename(result)}")
        else:
            self.app.log(f"❌ แปลง PDF อัตโนมัติไม่สำเร็จ: {result}")
