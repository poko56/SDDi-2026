import customtkinter as ctk

from ui.pages.base import BasePage
from ui.theme import ACCENT_PRIMARY, BG_SUBTLE, TEXT_MAIN, TEXT_MUTED, font
from ui.widgets import card

CONVERT_FOLDER_NAME = "auto_convert"


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
                                    command=getattr(self, "_toggle", None))
        self.switch.pack(anchor="w", padx=20, pady=(0, 20))

        log_card = card(self)
        log_card.pack(fill="both", expand=True, pady=10)
        ctk.CTkLabel(log_card, text="Activity Log", font=font(16, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(20, 10))
        self.txt_log = ctk.CTkTextbox(log_card, fg_color=BG_SUBTLE, text_color=TEXT_MAIN)
        self.txt_log.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.app.on_log(self._append_log)
        if hasattr(self, "_on_folder_changed"):
            self.app.on_folder_change(self._on_folder_changed)

    def _append_log(self, line):
        self.txt_log.insert("end", line)
        self.txt_log.see("end")
