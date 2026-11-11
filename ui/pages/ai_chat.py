import os
import re
from tkinter import messagebox

import customtkinter as ctk

from core.paths import safe_join
from ui.pages.base import BasePage
from ui.theme import (ACCENT_HOVER, ACCENT_PRIMARY, BG_CARD, BG_HOVER, TEXT_MAIN, TEXT_MUTED, Icons,
                      create_icon_image, font)
from ui.widgets import bind_mousewheel, reveal_in_file_manager

OPEN_MARKER_RE = re.compile(r"(\[OPEN:\s*[^\]]*\])")
AI_AVATAR_COLOR = "#10B981"


class AIChatPage(BasePage):
    title = "AI Help Chat"

    def build(self):
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x")
        self.lbl_provider = ctk.CTkLabel(bottom, text="", font=font(12), text_color=TEXT_MUTED)
        self.lbl_provider.pack(side="bottom", anchor="w", padx=60, pady=(0, 8))
        self.history = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.history.pack(side="top", fill="both", expand=True)

        inputs = ctk.CTkFrame(bottom, fg_color="transparent")
        inputs.pack(fill="x", padx=40, pady=20)
        self.entry = ctk.CTkEntry(inputs, placeholder_text="Ask ZipZap AI about your files...", fg_color=BG_CARD,
                                  text_color=TEXT_MAIN, height=50, corner_radius=25)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 15))
        self.entry.bind("<Return>", lambda event: self._send())
        ctk.CTkButton(inputs, text="", image=create_icon_image(Icons.SEND, "#FFFFFF", 20), command=self._send,
                      fg_color=ACCENT_PRIMARY, hover_color=ACCENT_HOVER, width=50, height=50,
                      corner_radius=25).pack(side="left")
        ctk.CTkButton(inputs, text="Clear", command=self._clear, fg_color="transparent", text_color=TEXT_MUTED,
                      hover_color=BG_HOVER, width=60, height=50, corner_radius=25).pack(side="left", padx=(10, 0))
        self._clear()

    def on_show(self):
        llm = self.services.llm
        if not llm.is_configured:
            text = f"⚠️ {llm.not_configured_message}"
        elif llm.keeps_data_local:
            text = f"🔒 {llm.label}: {llm.model_description} — ประมวลผลบนเครื่องนี้"
        else:
            text = f"☁️ {llm.label}: {llm.model_description}"
        self.lbl_provider.configure(text=text)

    def _history_canvas(self):
        return self.history._parent_canvas

    def _scroll_to_end(self):
        self.after(50, lambda: self._history_canvas().yview_moveto(1.0))

    def _clear(self):
        for widget in self.history.winfo_children():
            widget.destroy()
        banner = ctk.CTkFrame(self.history, fg_color="transparent")
        banner.pack(fill="x", pady=(80, 10))
        ctk.CTkLabel(banner, image=create_icon_image(Icons.SPARKLE, TEXT_MAIN, 48), text="").pack(pady=(0, 10))
        ctk.CTkLabel(banner, text="How can I help you today?", font=font(28, "bold"),
                     text_color=TEXT_MAIN).pack(pady=(10, 5))
        ctk.CTkLabel(banner, text="Ask me to find files, explain documents, or organize your storage.",
                     font=font(16), text_color=TEXT_MUTED).pack()
        bind_mousewheel(banner, self._history_canvas())

    def _message_row(self, is_user):
        row = ctk.CTkFrame(self.history, fg_color="transparent")
        row.pack(fill="x", pady=15)
        content = ctk.CTkFrame(row, fg_color="transparent")
        content.pack(fill="x", padx=40)
        avatar = ctk.CTkFrame(content, width=36, height=36, corner_radius=18,
                              fg_color=ACCENT_PRIMARY if is_user else AI_AVATAR_COLOR)
        avatar.pack(side="left", anchor="n", padx=(0, 20))
        avatar.pack_propagate(False)
        icon = Icons.PERSON if is_user else Icons.SPARKLE
        ctk.CTkLabel(avatar, image=create_icon_image(icon, "#FFFFFF", 20), text="").pack(expand=True)
        body = ctk.CTkFrame(content, fg_color="transparent")
        body.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(body, text="คุณ" if is_user else "ZipZap AI", font=font(15, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 5))
        return row, body

    def _add_message(self, text, is_user):
        row, body = self._message_row(is_user)
        self._render_body(body, text)
        bind_mousewheel(row, self._history_canvas())
        self._scroll_to_end()

    def _render_body(self, parent, text):
        """Plain text becomes labels; each [OPEN: path] marker becomes a button that reveals the file."""
        for segment in OPEN_MARKER_RE.split(text):
            if segment.startswith("[OPEN:") and segment.endswith("]"):
                rel_path = segment[len("[OPEN:"):-1].strip()
                if rel_path:
                    ctk.CTkButton(parent, text=f"📂 เปิดไฟล์: {os.path.basename(rel_path)}", height=30,
                                  corner_radius=8, fg_color=ACCENT_PRIMARY, hover_color=ACCENT_HOVER,
                                  font=font(13, "bold"),
                                  command=lambda p=rel_path: self._open(p)).pack(anchor="w", pady=4)
            elif segment.strip():
                ctk.CTkLabel(parent, text=segment.strip(), text_color=TEXT_MAIN, font=font(14), wraplength=700,
                             justify="left").pack(anchor="w")

    def _open(self, rel_path):
        path = safe_join(self.app.current_folder, rel_path)
        if path is None or not os.path.exists(path):
            messagebox.showerror("ไม่พบไฟล์", f"ไม่พบไฟล์ที่ระบุในโฟลเดอร์เป้าหมาย:\n{rel_path}")
            return
        try:
            reveal_in_file_manager(path)
        except OSError as e:
            messagebox.showerror("เกิดข้อผิดพลาด", f"ไม่สามารถเปิดไฟล์ได้: {e}")

    def _send(self):
        question = self.entry.get().strip()
        if not question:
            return
        self.entry.delete(0, "end")
        self._add_message(question, is_user=True)

        loading_row, body = self._message_row(is_user=False)
        ctk.CTkLabel(body, text="⏳ กำลังคิด...", text_color=TEXT_MUTED, font=font(14, slant="italic")).pack(anchor="w")
        self._scroll_to_end()

        folder = self.app.current_folder

        def show_reply(reply):
            loading_row.destroy()
            self._add_message(reply, is_user=False)

        self.app.run_background(lambda: self.services.assistant.ask_ai(folder, question), show_reply,
                                lambda e: show_reply(f"เกิดข้อผิดพลาด: {e}"))
