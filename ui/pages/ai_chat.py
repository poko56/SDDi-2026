import os
import re
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from core.paths import safe_join
from ui.pages.base import BasePage
from ui.theme import (ACCENT_HOVER, ACCENT_PRIMARY, BG_CARD, BG_HOVER, BORDER, TEXT_MAIN, TEXT_MUTED, Icons,
                      create_icon_image, font, resolve_color)
from ui.widgets import bind_mousewheel, reveal_in_file_manager

OPEN_MARKER_RE = re.compile(r"(\[OPEN:\s*[^\]]*\])")
AI_AVATAR_COLOR = "#10B981"
WARNING_COLOR = ("#B45309", "#FBBF24")
RING_SIZE = 22


class AIChatPage(BasePage):
    title = "AI Help Chat"

    PROVIDER_LABELS = {"zipzap": "ZipZap AI", "gemini": "Gemini", "ollama": "Local AI"}

    def build(self):
        self._provider_menu = None
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

        # Compact model + quota ring to the right of the input, like Claude Code's status chip
        self._build_model_chip(inputs)
        self._clear()

    # ---------- Model chip + quota ring ----------

    def _build_model_chip(self, parent):
        self.chip = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=20, border_width=1, border_color=BORDER)
        self.chip.pack(side="left", padx=(12, 0))
        inner = ctk.CTkFrame(self.chip, fg_color="transparent")
        inner.pack(padx=12, pady=6)
        self.chip_label = ctk.CTkLabel(inner, text="", font=font(12, "bold"), text_color=TEXT_MAIN)
        self.chip_label.pack(side="left", padx=(0, 10))
        self.ring = tk.Canvas(inner, width=RING_SIZE, height=RING_SIZE, highlightthickness=0,
                              bg=resolve_color(BG_CARD))
        self.ring.pack(side="left")
        # Click anywhere on the chip opens the provider menu
        for widget in (self.chip, inner, self.chip_label, self.ring):
            widget.bind("<Button-1>", lambda event: self._open_provider_menu())
            widget.configure(cursor="hand2")

    def _draw_ring(self, used, limit, color):
        """Circular arc filled proportionally to used/limit — same idea as Claude Code's usage indicator."""
        self.ring.delete("all")
        pad = 2
        box = (pad, pad, RING_SIZE - pad, RING_SIZE - pad)
        track = resolve_color(BORDER)
        self.ring.configure(bg=resolve_color(BG_CARD))
        # Background track
        self.ring.create_oval(*box, outline=track, width=3)
        if limit > 0 and used > 0:
            extent = -360 * min(used, limit) / limit  # Clockwise fill starting at 12 o'clock
            self.ring.create_arc(*box, start=90, extent=extent, style="arc",
                                 outline=resolve_color(color), width=3)

    def _refresh_chip(self, usage=None):
        """Chip text = provider · model; ring = today's usage for ZipZap AI, empty for others."""
        llm = self.services.llm
        name = llm.label
        self.chip_label.configure(text=name)
        if llm.active_name == "zipzap":
            if usage is None:
                # Fire off a background fetch; the ring stays empty until it returns
                self._draw_ring(0, 1, TEXT_MUTED)
                if self.services.zipzap.session:
                    self.app.run_background(self.services.zipzap.usage, on_done=self._on_usage)
                return
            if usage.get("expired") or self.services.zipzap.session == "":
                self._draw_ring(0, 1, WARNING_COLOR)
                return
            used, limit = usage.get("used", 0), usage.get("limit", 50)
            if used >= limit:
                color = WARNING_COLOR
            elif used >= limit * 0.8:
                color = ("#F59E0B", "#FBBF24")  # Amber when almost out
            else:
                color = ACCENT_PRIMARY
            self._draw_ring(used, limit, color)
            self.chip_label.configure(text=f"{name}  {used}/{limit}")
        else:
            # Non-ZipZap providers: no quota to show, so draw a solid dot in brand colour
            self._draw_ring(1, 1, ACCENT_PRIMARY if llm.is_configured else WARNING_COLOR)

    def _on_usage(self, usage):
        try:
            self._refresh_chip(usage)
        except tk.TclError:
            pass  # The chat page was torn down before the background fetch returned

    # ---------- Provider menu ----------

    def _open_provider_menu(self):
        if self._provider_menu is not None and self._provider_menu.winfo_exists():
            self._close_provider_menu()
            return
        menu = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
        self._provider_menu = menu
        for key, label in self.PROVIDER_LABELS.items():
            row = ctk.CTkFrame(menu, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=2)
            active = key == self.services.llm.active_name
            ctk.CTkButton(row, text=f"  {'✓' if active else '  '}  {label}", anchor="w",
                          fg_color=BG_HOVER if active else "transparent", hover_color=BG_HOVER,
                          text_color=ACCENT_PRIMARY if active else TEXT_MAIN,
                          width=200, height=32, font=font(13, "bold" if active else "normal"),
                          command=lambda k=key: self._pick_provider(k)).pack(fill="x")
        menu.update_idletasks()
        chip = self.chip
        self.update_idletasks()
        # Anchor the menu just above the chip
        x = chip.winfo_rootx() - self.winfo_rootx() + chip.winfo_width() - menu.winfo_width()
        y = chip.winfo_rooty() - self.winfo_rooty() - menu.winfo_height() - 6
        menu.place(x=max(x, 10), y=max(y, 10))
        # CustomTkinter blocks bind_all on CTk widgets; go through tk.Misc on the toplevel root
        self.after(10, lambda: tk.Misc.bind_all(self.winfo_toplevel(), "<Button-1>",
                                                self._maybe_close_menu, add="+"))

    def _maybe_close_menu(self, event):
        widget = event.widget
        while widget is not None:
            if widget is self._provider_menu or widget is self.chip:
                return
            widget = getattr(widget, "master", None)
        self._close_provider_menu()

    def _close_provider_menu(self):
        if self._provider_menu is not None:
            tk.Misc.unbind_all(self.winfo_toplevel(), "<Button-1>")
            try:
                self._provider_menu.destroy()
            except tk.TclError:
                pass
            self._provider_menu = None

    def _pick_provider(self, key):
        self._close_provider_menu()
        self.services.set_ai_provider(key)
        self._refresh_provider_label()
        self._refresh_chip()
        self.app.log(f"🤖 เปลี่ยน AI เป็น {self.services.llm.label}")

    # ---------- Provider status (bottom line) ----------

    def on_show(self):
        self._refresh_provider_label()
        self._refresh_chip()

    def _refresh_provider_label(self):
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
        self._welcome_banner = banner  # Removed as soon as the first message arrives

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
        banner = getattr(self, "_welcome_banner", None)
        if banner is not None and banner.winfo_exists():
            banner.destroy()
            self._welcome_banner = None
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
            self._refresh_chip()  # Pull the new remaining-quota number from the server after each reply

        self.app.run_background(lambda: self.services.assistant.ask_ai(folder, question), show_reply,
                                lambda e: show_reply(f"เกิดข้อผิดพลาด: {e}"))
