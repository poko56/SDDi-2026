import webbrowser
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.ollama import RECOMMENDED_MODELS, recommend_model
from core.system_info import total_memory_gb
from ui.pages.base import BasePage
from ui.theme import (ACCENT_DANGER, ACCENT_HOVER, ACCENT_PRIMARY, ACCENT_SOFT, ACCENT_SUCCESS, BG_HOVER, BG_SUBTLE,
                      BORDER, TEXT_MAIN, TEXT_MUTED, Icons, create_icon_image, font)
from ui.widgets import card

APP_VERSION = "1.2.3"
OLLAMA_DOWNLOAD_URL = "https://ollama.com/download"
WARNING_COLOR = ("#B45309", "#FBBF24")
SUCCESS_SOFT = ("#D1FAE5", "#064E3B")
WARNING_SOFT = ("#FEF3C7", "#78350F")
DANGER_SOFT = ("#FEE2E2", "#7F1D1D")
PROVIDER_LABELS = {"zipzap": "ZipZap AI (login Google)", "gemini": "Gemini (key ของตัวเอง)",
                   "ollama": "Local AI (Ollama)"}


class SettingsPage(BasePage):
    title = "Settings"

    def build(self):
        self._installed_models = []
        self._downloading = False
        self._status_pills = {}
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._build_provider_card(scroll)
        self._build_zipzap_card(scroll)
        self._build_api_card(scroll)
        self._build_local_card(scroll)
        self._build_exclusions_card(scroll)
        self._build_about_card(scroll)

    def on_show(self):
        self._refresh_local_status()
        self._refresh_account()  # Re-fetch today's ZipZap AI usage after the user chatted elsewhere

    def _section(self, parent, title, subtitle, icon=None, icon_color=ACCENT_PRIMARY, key=None):
        """Card with an icon badge + title + subtitle header and a divider under it."""
        box = card(parent)
        box.pack(fill="x", pady=(0, 14))
        header = ctk.CTkFrame(box, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(18, 10))
        if icon is not None:
            badge = ctk.CTkFrame(header, width=36, height=36, corner_radius=10, fg_color=ACCENT_SOFT)
            badge.pack(side="left", padx=(0, 14))
            badge.pack_propagate(False)
            ctk.CTkLabel(badge, text="", image=create_icon_image(icon, icon_color, 20)).pack(expand=True)
        body = ctk.CTkFrame(header, fg_color="transparent")
        body.pack(side="left", fill="x", expand=True)
        title_row = ctk.CTkFrame(body, fg_color="transparent")
        title_row.pack(fill="x")
        ctk.CTkLabel(title_row, text=title, font=font(16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        if key is not None:
            pill = self._status_pill(title_row)
            pill.pack(side="right")
            self._status_pills[key] = pill
        ctk.CTkLabel(body, text=subtitle, font=font(12), text_color=TEXT_MUTED,
                     justify="left").pack(anchor="w", pady=(2, 0))
        ctk.CTkFrame(box, height=1, fg_color=BORDER).pack(fill="x", padx=22)
        return box

    def _status_pill(self, parent):
        return ctk.CTkLabel(parent, text="", font=font(11, "bold"), fg_color=BG_HOVER,
                            text_color=TEXT_MUTED, corner_radius=10, padx=10, pady=4)

    def _set_pill(self, key, text, fg=None, bg=None):
        pill = self._status_pills.get(key)
        if pill is None:
            return
        pill.configure(text=f"  {text}  ", text_color=fg or TEXT_MUTED, fg_color=bg or BG_HOVER)

    @staticmethod
    def _small_button(parent, text, command, primary=False, **kwargs):
        style = ({"fg_color": ACCENT_PRIMARY, "hover_color": ACCENT_HOVER} if primary
                 else {"fg_color": BG_HOVER, "hover_color": BORDER, "text_color": TEXT_MAIN})
        return ctk.CTkButton(parent, text=text, command=command, height=34, **style, **kwargs)

    # ---------- Provider ----------

    def _build_provider_card(self, parent):
        box = self._section(parent, "ผู้ให้บริการ AI",
                            "เลือกว่าจะให้ AI Chat และ Smart Rename ประมวลผลที่ไหน",
                            icon=Icons.SPARKLE)
        self.var_provider = ctk.StringVar(value=PROVIDER_LABELS[self.services.llm.active_name])
        ctk.CTkSegmentedButton(box, values=list(PROVIDER_LABELS.values()), variable=self.var_provider,
                               command=self._on_provider_change,
                               selected_color=ACCENT_PRIMARY, selected_hover_color=ACCENT_HOVER,
                               ).pack(fill="x", padx=22, pady=(14, 10))
        self.lbl_privacy = ctk.CTkLabel(box, text="", font=font(13, "bold"), justify="left", wraplength=640)
        self.lbl_privacy.pack(anchor="w", padx=22, pady=(0, 18))
        self._refresh_privacy_label()

    def _on_provider_change(self, label):
        name = next(k for k, v in PROVIDER_LABELS.items() if v == label)
        self.services.set_ai_provider(name)
        self._refresh_privacy_label()
        self._refresh_about()
        self.app.log(f"🤖 เปลี่ยนผู้ให้บริการ AI เป็น {label}")

    def _refresh_privacy_label(self):
        llm = self.services.llm
        if not llm.is_configured:
            text, color = f"⚠️ {llm.label} ยังไม่พร้อมใช้งาน — ตั้งค่าในส่วนด้านล่าง", WARNING_COLOR
        elif llm.keeps_data_local:
            text, color = "🔒 ประมวลผลบนเครื่องนี้ รายชื่อไฟล์และเนื้อหาไฟล์ไม่ออกจากเครื่อง", ACCENT_SUCCESS
        elif llm.active_name == "ollama":
            text, color = f"🌐 ส่งข้อมูลไปที่ Ollama server {llm.base_url} (นอกเครื่องนี้)", WARNING_COLOR
        elif llm.active_name == "zipzap":
            text, color = "☁️ ส่งไปประมวลผลที่ Google ผ่าน server ของทีม ZipZap — ไม่ต้องใช้ key", TEXT_MUTED
        else:
            text, color = "☁️ รายชื่อไฟล์และเนื้อหาไฟล์ที่ให้ AI อ่านจะถูกส่งไปประมวลผลที่ Google", TEXT_MUTED
        self.lbl_privacy.configure(text=text, text_color=color)

    # ---------- ZipZap AI (Google sign-in) ----------

    def _build_zipzap_card(self, parent):
        self.card_zipzap = self._section(
            parent, "ZipZap AI",
            "login ด้วยบัญชี Google เพื่อใช้ AI ของทีมได้ฟรี วันละจำนวนจำกัด\n"
            "ZipZap ได้รับแค่อีเมลและชื่อ ไม่ได้รับรหัสผ่านหรือสิทธิ์เข้าถึงบัญชี Google",
            icon=Icons.PERSON, key="zipzap")
        row = ctk.CTkFrame(self.card_zipzap, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=(14, 18))
        self.lbl_account = ctk.CTkLabel(row, text="", font=font(13, "bold"), justify="left", anchor="w")
        self.lbl_account.pack(side="left", fill="x", expand=True)
        self.btn_login = self._small_button(row, "", self._toggle_login, primary=True, width=180)
        self.btn_login.pack(side="right")
        self._signing_in = False
        self._refresh_account()

    def _refresh_account(self):
        if self.services.zipzap.session:
            email = self.services.config.get("zipzap_email")
            self.lbl_account.configure(text=f"login แล้ว: {email}\nกำลังตรวจโควตาวันนี้...",
                                       text_color=ACCENT_SUCCESS)
            self.btn_login.configure(text="Logout", state="normal",
                                     fg_color=BG_HOVER, hover_color=BORDER, text_color=TEXT_MAIN)
            self._set_pill("zipzap", "LOGIN แล้ว", ACCENT_SUCCESS, SUCCESS_SOFT)
            self.app.run_background(self.services.zipzap.usage, on_done=self._show_usage)
        else:
            self.lbl_account.configure(text="ยังไม่ได้ login", text_color=TEXT_MUTED)
            self.btn_login.configure(text="Login ด้วย Google", state="normal",
                                     fg_color=ACCENT_PRIMARY, hover_color=ACCENT_HOVER, text_color="#FFFFFF")
            self._set_pill("zipzap", "ยังไม่ LOGIN", TEXT_MUTED, BG_HOVER)
        self.app.refresh_account_chip()

    def _show_usage(self, usage):
        if not self.services.zipzap.session or self._signing_in:
            return
        if usage is not None and usage.get("expired"):
            expired = "⚠️ login ZipZap AI หมดอายุ กรุณา login ใหม่"
            self.app.run_background(self.services.sign_out, on_done=lambda _: self._after_auth_change(expired))
            return
        email = self.services.config.get("zipzap_email")
        if usage is None:
            quota, color = "⚠️ ติดต่อ server ของ ZipZap ไม่ได้ ตรวจอินเทอร์เน็ต", WARNING_COLOR
            self._set_pill("zipzap", "เชื่อมต่อไม่ได้", WARNING_COLOR, WARNING_SOFT)
        elif usage.get("remaining", 0) <= 0:
            quota, color = f"⚠️ ใช้ครบ {usage['limit']} ครั้งของวันนี้แล้ว ใช้ได้อีกครั้งหลังเที่ยงคืน", WARNING_COLOR
            self._set_pill("zipzap", "โควตาหมด", WARNING_COLOR, WARNING_SOFT)
        else:
            quota, color = f"วันนี้ใช้ไป {usage['used']}/{usage['limit']} ครั้ง", ACCENT_SUCCESS
            self._set_pill("zipzap", f"{usage['used']}/{usage['limit']}", ACCENT_SUCCESS, SUCCESS_SOFT)
        self.lbl_account.configure(text=f"login แล้ว: {email}\n{quota}", text_color=color)

    def _toggle_login(self):
        if self._signing_in:
            return
        if self.services.zipzap.session:
            self.btn_login.configure(state="disabled")
            self.app.run_background(self.services.sign_out,
                                    on_done=lambda _: self._after_auth_change("👋 logout ZipZap AI แล้ว"))
            return
        self._signing_in = True
        self.btn_login.configure(text="รอ login ใน browser...", state="disabled")
        self.lbl_account.configure(text="เปิด browser ให้เลือกบัญชี Google แล้ว\nlogin เสร็จแล้วกลับมาที่หน้านี้",
                                   text_color=TEXT_MUTED)
        self.app.run_background(self.services.sign_in_with_google,
                                on_done=self._on_signed_in, on_error=self._on_sign_in_failed)

    def _on_signed_in(self, result):
        self._signing_in = False
        self._after_auth_change(f"🔐 login ZipZap AI ด้วย {result.get('email', '')}")

    def _on_sign_in_failed(self, error):
        self._signing_in = False
        self._refresh_account()
        self.lbl_account.configure(text=f"⚠️ {error}", text_color=WARNING_COLOR)

    def _after_auth_change(self, log_message):
        self.app.log(log_message)
        self._refresh_account()
        self._refresh_privacy_label()
        self._refresh_about()

    # ---------- Gemini ----------

    def _build_api_card(self, parent):
        subtitle = ("รับ key ฟรีได้ที่ aistudio.google.com\n"
                    "key ถูกเก็บในเครื่องนี้เท่านั้น (~/.zipzap/config.json) ไม่ได้ฝังไว้ในตัวโปรแกรม")
        self.card_gemini = self._section(parent, "Gemini API Key", subtitle, icon=Icons.EDIT, key="gemini")
        row = ctk.CTkFrame(self.card_gemini, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=(14, 8))
        self.entry_key = ctk.CTkEntry(row, show="•", placeholder_text="วาง API key ที่นี่", fg_color=BG_SUBTLE,
                                      text_color=TEXT_MAIN, height=38, corner_radius=10)
        self.entry_key.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._small_button(row, "บันทึก", self._save_key, primary=True, width=80).pack(side="left")
        self._small_button(row, "ลบ key", self._clear_key, width=70).pack(side="left", padx=(8, 0))
        self.lbl_key_status = ctk.CTkLabel(self.card_gemini, text="", font=font(13, "bold"))
        self.lbl_key_status.pack(anchor="w", padx=22, pady=(0, 18))
        self._refresh_key_status()

    def _refresh_key_status(self):
        if self.services.gemini.is_configured:
            saved = self.services.config.get("gemini_api_key")
            source = "บันทึกไว้ใน Settings" if saved else "จาก environment / ไฟล์นักพัฒนา"
            self.lbl_key_status.configure(text=f"มี API Key แล้ว ({source})", text_color=ACCENT_SUCCESS)
            self._set_pill("gemini", "ตั้งค่าแล้ว", ACCENT_SUCCESS, SUCCESS_SOFT)
        else:
            self.lbl_key_status.configure(text="ยังไม่มี API Key", text_color=ACCENT_DANGER)
            self._set_pill("gemini", "ยังไม่ตั้งค่า", ACCENT_DANGER, DANGER_SOFT)

    def _save_key(self):
        key = self.entry_key.get().strip()
        if not key:
            return
        self.services.set_api_key(key)
        self.entry_key.delete(0, "end")
        self._refresh_key_status()
        self._refresh_privacy_label()
        self.app.log("🔑 บันทึก Gemini API Key แล้ว")

    def _clear_key(self):
        self.services.set_api_key("")
        self._refresh_key_status()
        self._refresh_privacy_label()
        self.app.log("🔑 ลบ Gemini API Key ที่บันทึกไว้แล้ว")

    # ---------- Local AI (Ollama) ----------

    def _build_local_card(self, parent):
        self.card_ollama = self._section(parent, "Local AI (Ollama)",
                                         "รัน AI บนเครื่องนี้ ใช้ได้แม้ไม่มีอินเทอร์เน็ต และไฟล์ไม่ถูกส่งออกไปไหน\n"
                                         "ขั้นตอน: 1) ติดตั้งโปรแกรม Ollama  2) ดาวน์โหลดโมเดล  3) กด 'ใช้โมเดลนี้'",
                                         icon=Icons.MONITOR, key="ollama")
        box = self.card_ollama
        status_row = ctk.CTkFrame(box, fg_color="transparent")
        status_row.pack(fill="x", padx=22, pady=(14, 0))
        self.lbl_ollama_status = ctk.CTkLabel(status_row, text="กำลังตรวจสอบ Ollama...", font=font(13, "bold"),
                                              text_color=TEXT_MUTED)
        self.lbl_ollama_status.pack(side="left")
        self._small_button(status_row, "ตรวจสอบอีกครั้ง", self._refresh_local_status, width=110).pack(side="right")
        self.btn_install_ollama = self._small_button(status_row, "ดาวน์โหลด Ollama",
                                                     lambda: webbrowser.open(OLLAMA_DOWNLOAD_URL), primary=True,
                                                     width=130)

        ram = total_memory_gb()
        self._recommended = recommend_model(ram)
        ram_text = f"เครื่องนี้มี RAM {ram:.0f} GB" if ram else "อ่านขนาด RAM ไม่ได้"
        if self._recommended:
            advice = f" → แนะนำ {self._recommended.name} (ไฟล์ประมาณ {self._recommended.size_gb} GB)"
        else:
            advice = " → RAM น้อยเกินไปสำหรับ Local AI แนะนำให้ใช้ Gemini"
        ctk.CTkLabel(box, text=ram_text + advice, font=font(12), text_color=TEXT_MUTED).pack(anchor="w", padx=22,
                                                                                             pady=(6, 0))

        model_row = ctk.CTkFrame(box, fg_color="transparent")
        model_row.pack(fill="x", padx=22, pady=(8, 0))
        initial = self.services.ollama.model or (self._recommended or RECOMMENDED_MODELS[-1]).name
        self.var_model = ctk.StringVar(value=initial)
        self.menu_model = ctk.CTkOptionMenu(model_row, variable=self.var_model, values=[initial], width=220,
                                            command=lambda _: self._update_model_buttons(), fg_color=BG_SUBTLE,
                                            text_color=TEXT_MAIN, button_color=BG_HOVER, button_hover_color=BORDER)
        self.menu_model.pack(side="left")
        self.btn_pull = self._small_button(model_row, "ดาวน์โหลดโมเดล", self._pull_model, width=130)
        self.btn_pull.pack(side="left", padx=(10, 0))
        self.btn_use = self._small_button(model_row, "ใช้โมเดลนี้", self._use_model, primary=True, width=110)
        self.btn_use.pack(side="left", padx=(10, 0))
        self.lbl_model_note = ctk.CTkLabel(box, text="", font=font(12), text_color=TEXT_MUTED, justify="left")
        self.lbl_model_note.pack(anchor="w", padx=22, pady=(4, 0))

        self.progress = ctk.CTkProgressBar(box, progress_color=ACCENT_PRIMARY)
        self.progress.set(0)
        self.lbl_progress = ctk.CTkLabel(box, text="", font=font(12), text_color=TEXT_MUTED)

        url_row = ctk.CTkFrame(box, fg_color="transparent")
        url_row.pack(fill="x", padx=22, pady=(10, 18))
        ctk.CTkLabel(url_row, text="Ollama server", font=font(12), text_color=TEXT_MUTED).pack(side="left")
        self.entry_url = ctk.CTkEntry(url_row, fg_color=BG_SUBTLE, text_color=TEXT_MAIN, height=30)
        self.entry_url.insert(0, self.services.ollama.base_url)
        self.entry_url.pack(side="left", fill="x", expand=True, padx=10)
        self._small_button(url_row, "บันทึก URL", self._save_url, width=90).pack(side="left")

    def _refresh_local_status(self):
        ollama = self.services.ollama

        def check():
            version = ollama.server_version()
            models = ollama.installed_models() if version else []
            return version, models

        def show(result):
            version, models = result
            self._installed_models = models
            if version:
                self.lbl_ollama_status.configure(text=f"Ollama ทำงานอยู่ (v{version}) — มีโมเดล {len(models)} ตัว",
                                                 text_color=ACCENT_SUCCESS)
                self.btn_install_ollama.pack_forget()
                self._set_pill("ollama", "พร้อมใช้", ACCENT_SUCCESS, SUCCESS_SOFT)
            else:
                self.lbl_ollama_status.configure(text=f"ไม่พบ Ollama ที่ {ollama.base_url}",
                                                 text_color=ACCENT_DANGER)
                self.btn_install_ollama.pack(side="right", padx=(0, 10))
                self._set_pill("ollama", "ยังไม่ได้ติดตั้ง", ACCENT_DANGER, DANGER_SOFT)
            recommended = [m.name for m in RECOMMENDED_MODELS]
            choices = recommended + [m for m in models if m not in recommended]
            self.menu_model.configure(values=choices)
            self._ollama_running = bool(version)
            self._update_model_buttons()
            self._refresh_privacy_label()

        self._ollama_running = False
        self.app.run_background(check, show, lambda e: show((None, [])))

    def _is_installed(self, name):
        # Ollama lists "gemma3:4b"; a bare "llama3" means "llama3:latest"
        full = name if ":" in name else f"{name}:latest"
        return full in self._installed_models or name in self._installed_models

    def _update_model_buttons(self):
        name = self.var_model.get()
        installed = self._is_installed(name)
        running = getattr(self, "_ollama_running", False)
        can_pull = running and not installed and not self._downloading
        self.btn_pull.configure(state="normal" if can_pull else "disabled")
        # CustomTkinter keeps a disabled button's colour, so grey it out explicitly
        self.btn_use.configure(state="normal" if installed else "disabled",
                               fg_color=ACCENT_PRIMARY if installed else BG_HOVER)
        info = next((m for m in RECOMMENDED_MODELS if m.name == name), None)
        note = "✅ ดาวน์โหลดแล้ว" if installed else "ยังไม่ได้ดาวน์โหลด"
        if info:
            note += f" · ประมาณ {info.size_gb} GB · {info.note}"
        if self.services.ollama.model == name:
            note += " · กำลังใช้งาน"
        self.lbl_model_note.configure(text=note)

    def _pull_model(self):
        name = self.var_model.get()
        info = next((m for m in RECOMMENDED_MODELS if m.name == name), None)
        size = f"ประมาณ {info.size_gb} GB" if info else "หลาย GB"
        question = f"ดาวน์โหลดโมเดล {name} ({size}) จาก Ollama?\nอาจใช้เวลาหลายนาทีขึ้นกับความเร็วอินเทอร์เน็ต"
        if not messagebox.askyesno("ดาวน์โหลดโมเดล", question):
            return
        self._downloading = True
        self._update_model_buttons()
        self.progress.set(0)
        self.progress.pack(fill="x", padx=20, pady=(8, 0), before=self.entry_url.master)
        self.lbl_progress.pack(anchor="w", padx=20, before=self.entry_url.master)
        self.app.log(f"⬇️ เริ่มดาวน์โหลดโมเดล {name}")

        def on_progress(status, completed, total):
            self.app.call_in_ui(self._show_progress, status, completed, total)

        def finished(_):
            self._downloading = False
            self.lbl_progress.configure(text=f"✅ ดาวน์โหลด {name} เสร็จแล้ว กด 'ใช้โมเดลนี้' เพื่อเริ่มใช้งาน")
            self.app.log(f"✅ ดาวน์โหลดโมเดล {name} เสร็จแล้ว")
            self._refresh_local_status()

        def failed(error):
            self._downloading = False
            self.lbl_progress.configure(text=f"❌ {error}")
            self.app.log(f"❌ ดาวน์โหลดโมเดล {name} ไม่สำเร็จ: {error}")
            self._update_model_buttons()

        self.app.run_background(lambda: self.services.ollama.pull_model(name, on_progress), finished, failed)

    def _show_progress(self, status, completed, total):
        if total:
            self.progress.set(completed / total)
            self.lbl_progress.configure(text=f"{status} — {completed / 1024 ** 3:.2f} / {total / 1024 ** 3:.2f} GB")
        else:
            self.lbl_progress.configure(text=status)

    def _use_model(self):
        name = self.var_model.get()
        self.services.set_local_ai(self.services.ollama.base_url, name)
        self.services.set_ai_provider("ollama")
        self.var_provider.set(PROVIDER_LABELS["ollama"])
        self._update_model_buttons()
        self._refresh_privacy_label()
        self._refresh_about()
        self.app.log(f"🤖 ใช้ Local AI: {name}")

    def _save_url(self):
        try:
            self.services.set_local_ai(self.entry_url.get(), self.services.ollama.model)
        except ValueError as e:
            messagebox.showerror("Ollama server", str(e))
            return
        self.entry_url.delete(0, "end")
        self.entry_url.insert(0, self.services.ollama.base_url)
        self.app.log(f"🔗 ตั้ง Ollama server เป็น {self.services.ollama.base_url}")
        self._refresh_local_status()

    # ---------- Excluded folders ----------

    def _build_exclusions_card(self, parent):
        box = self._section(parent, "โฟลเดอร์ยกเว้น",
                            "Cleaner, การจัดไฟล์ และ Auto Monitor จะไม่แตะไฟล์ในโฟลเดอร์เหล่านี้",
                            icon=Icons.FOLDER)
        self.exclusion_list = ctk.CTkFrame(box, fg_color="transparent")
        self.exclusion_list.pack(fill="x", padx=22, pady=(14, 0))
        add_button = self._small_button(box, "+ เพิ่มโฟลเดอร์", self._add_exclusion, width=140)
        add_button.pack(anchor="w", padx=22, pady=(8, 18))
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
        box = self._section(parent, "About ZipZap", f"Version {APP_VERSION}\nPython + CustomTkinter",
                            icon=Icons.SETTINGS)
        self.lbl_about_ai = ctk.CTkLabel(box, text="", font=font(12), text_color=TEXT_MUTED, justify="left")
        self.lbl_about_ai.pack(anchor="w", padx=22, pady=(14, 18))
        self._refresh_about()

    def _refresh_about(self):
        llm = self.services.llm
        self.lbl_about_ai.configure(text=f"AI ที่ใช้อยู่: {llm.label} — {llm.model_description}")
