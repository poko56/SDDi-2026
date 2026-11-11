import os
import queue
import threading
import tkinter as tk
from datetime import datetime

import customtkinter as ctk
from PIL import Image

from core.paths import resource_path
from ui.pages.ai_chat import AIChatPage
from ui.pages.cleaner import CleanerPage
from ui.pages.converter import ConverterPage
from ui.pages.dashboard import DashboardPage
from ui.pages.monitor import MonitorPage
from ui.pages.settings import SettingsPage
from ui.theme import (ACCENT_HOVER, ACCENT_PRIMARY, ACCENT_SOFT, ACCENT_SUCCESS, BG_CARD, BG_HOVER, BG_MAIN, BORDER,
                      SIDEBAR_BG, TEXT_MAIN, TEXT_MUTED, Icons, create_icon_image, font)

WARNING_COLOR = ("#B45309", "#FBBF24")
UI_POLL_MS = 50
PREFERRED_SIZE = (1200, 800)
MIN_SIZE = (960, 600)
SCREEN_MARGIN = (40, 100)  # Leave room for the menu bar, dock or taskbar


class ZipZapApp(ctk.CTk):
    """Main window: sidebar navigation, shared state and the bridge between worker threads and Tk.

    Pages never talk to each other directly. They read `current_folder`, and
    subscribe to folder changes and log messages (Observer pattern), so a page
    can be added or removed without touching the others.
    """

    PAGES = [
        ("dashboard", "Dashboard", Icons.DASHBOARD, DashboardPage),
        ("cleaner", "Smart Cleaner", Icons.CLEANER, CleanerPage),
        ("converter", "Converter", Icons.CONVERTER, ConverterPage),
        ("ai", "AI Help Chat", Icons.AI, AIChatPage),
        ("monitor", "Auto Monitor", Icons.MONITOR, MonitorPage),
        ("settings", "Settings", Icons.SETTINGS, SettingsPage),
    ]

    def __init__(self, services):
        super().__init__()
        self.services = services
        self.current_folder = ""
        self._folder_listeners = []
        self._log_listeners = []
        self._ui_queue = queue.Queue()
        self._account_popup = None

        ctk.set_appearance_mode(services.config.get("theme"))
        self.title("ZipZap - Smart File Manager")
        self._fit_to_screen()
        self.configure(fg_color=BG_MAIN)
        self._set_window_icon()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self._build_sidebar()
        self._build_content_area()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(UI_POLL_MS, self._drain_ui_queue)
        self.show_page("dashboard")

    # ---------- Threading ----------

    def call_in_ui(self, func, *args):
        """Schedule func(*args) on the Tk main thread. Safe to call from any thread."""
        self._ui_queue.put((func, args))

    def _drain_ui_queue(self):
        try:
            while True:
                try:
                    func, args = self._ui_queue.get_nowait()
                except queue.Empty:
                    break
                self._run_ui_callback(func, args)
        finally:
            # Always re-arm: if this stopped, every later background result would be lost
            self.after(UI_POLL_MS, self._drain_ui_queue)

    def _run_ui_callback(self, func, args):
        try:
            func(*args)
        except tk.TclError:
            pass  # The widget was destroyed before the update arrived
        except Exception as e:  # One failing update must not block the ones after it
            self.services.logger.log_action("ERROR", f"UI update {getattr(func, '__name__', func)} failed: {e!r}")
            if func not in self._log_listeners:  # Reporting a broken log view through itself would loop
                self.log(f"❌ เกิดข้อผิดพลาดในหน้าจอ: {e}")

    def run_background(self, task, on_done=None, on_error=None):
        """Run task() on a worker thread.

        Its result goes to on_done (or the exception to on_error), called on the UI thread.
        """
        def worker():
            try:
                result = task()
            except Exception as e:  # Report any worker failure instead of losing it silently
                if on_error:
                    self.call_in_ui(on_error, e)
                else:
                    self.log(f"❌ เกิดข้อผิดพลาด: {e}")
                return
            if on_done:
                self.call_in_ui(on_done, result)

        threading.Thread(target=worker, daemon=True).start()

    # ---------- Shared state (Observer) ----------

    def on_folder_change(self, listener):
        self._folder_listeners.append(listener)

    def set_folder(self, folder):
        self.current_folder = folder
        for listener in self._folder_listeners:
            listener(folder)

    def on_log(self, listener):
        self._log_listeners.append(listener)

    def log(self, message):
        """Add a line to the activity logs. Safe to call from any thread."""
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n"
        for listener in self._log_listeners:
            self.call_in_ui(listener, line)

    # ---------- Layout ----------

    def _fit_to_screen(self):
        """Open at the preferred size, shrunk to fit small screens such as a 1280x720 projector."""
        width = min(PREFERRED_SIZE[0], self.winfo_screenwidth() - SCREEN_MARGIN[0])
        height = min(PREFERRED_SIZE[1], self.winfo_screenheight() - SCREEN_MARGIN[1])
        width, height = max(width, MIN_SIZE[0]), max(height, MIN_SIZE[1])
        x = max((self.winfo_screenwidth() - width) // 2, 0)
        y = max((self.winfo_screenheight() - height) // 3, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(*MIN_SIZE)
        self.resizable(True, True)

    def _set_window_icon(self):
        try:
            if os.name == "nt":
                self.iconbitmap(resource_path("icon.ico"))
            else:
                self._icon = tk.PhotoImage(file=resource_path("icon.png"))
                self.iconphoto(False, self._icon)
        except tk.TclError:
            pass

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=SIDEBAR_BG)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(len(self.PAGES) + 1, weight=1)

        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        try:
            logo = Image.open(resource_path("assets", "logo_transparent.png")).convert("RGBA")
            width = 180
            height = int(logo.height * width / logo.width)
            logo = logo.resize((width * 2, height * 2), Image.Resampling.LANCZOS)  # 2x for Retina
            self._logo = ctk.CTkImage(light_image=logo, size=(width, height))
            ctk.CTkLabel(logo_frame, image=self._logo, text="").pack(side="left")
        except OSError:
            ctk.CTkLabel(logo_frame, text="⚡ ZipZap", font=font(24, "bold"),
                         text_color=ACCENT_PRIMARY).pack(side="left")

        self._nav_buttons = {}
        for row, (key, label, icon, _) in enumerate(self.PAGES, start=1):
            btn = ctk.CTkButton(
                sidebar, text=f"  {label}", image=create_icon_image(icon, TEXT_MUTED),
                command=lambda k=key: self.show_page(k), fg_color="transparent", text_color=TEXT_MUTED,
                hover_color=BG_MAIN, font=font(14, "bold"), anchor="w", height=45,
            )
            btn.grid(row=row, column=0, padx=15, pady=5, sticky="ew")
            btn.icons = (create_icon_image(icon, ACCENT_PRIMARY), create_icon_image(icon, TEXT_MUTED))
            self._nav_buttons[key] = btn

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.grid(row=len(self.PAGES) + 2, column=0, padx=15, pady=(10, 18), sticky="ew")
        self.switch_theme = ctk.CTkSwitch(footer, text="Dark Mode", command=self._toggle_theme,
                                          progress_color=ACCENT_PRIMARY)
        self.switch_theme.pack(side="left", padx=(5, 0))
        if self.services.config.get("theme") == "Dark":
            self.switch_theme.select()

        self.btn_account = ctk.CTkButton(footer, text="", command=self._account_action, width=38, height=38,
                                         corner_radius=19, font=font(15, "bold"))
        self.btn_account.pack(side="right", padx=(0, 4))
        self.refresh_account_chip()

    def _build_content_area(self):
        main = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")

        topbar = ctk.CTkFrame(main, height=60, fg_color=BG_CARD, corner_radius=0)
        topbar.pack(fill="x")
        self.lbl_page_title = ctk.CTkLabel(topbar, text="", font=font(20, "bold"), text_color=TEXT_MAIN)
        self.lbl_page_title.pack(side="left", padx=30, pady=15)

        container = ctk.CTkFrame(main, fg_color="transparent")
        container.pack(fill="both", expand=True)
        self.pages = {key: page_cls(container, self) for key, _, _, page_cls in self.PAGES}

    def show_page(self, key):
        for page_key, btn in self._nav_buttons.items():
            active = page_key == key
            btn.configure(
                fg_color=ACCENT_SOFT if active else "transparent",
                text_color=ACCENT_PRIMARY if active else TEXT_MUTED,
                image=btn.icons[0] if active else btn.icons[1],
            )
        for page in self.pages.values():
            page.pack_forget()
        page = self.pages[key]
        self.lbl_page_title.configure(text=page.title)
        page.pack(fill="both", expand=True, padx=30, pady=20)
        page.on_show()

    def refresh_account_chip(self):
        """Render the avatar by the Dark Mode switch to match sign-in state. Safe to call from Settings."""
        if self.services.zipzap.session:
            email = self.services.config.get("zipzap_email") or "G"
            self.btn_account.configure(text=(email[:1].upper() or "G"), image=None,
                                       fg_color=ACCENT_PRIMARY, text_color="#FFFFFF", hover_color=ACCENT_HOVER)
        else:
            self.btn_account.configure(text="", image=create_icon_image(Icons.PERSON, TEXT_MUTED, 18),
                                       fg_color=BG_HOVER, hover_color=BORDER)
        if self._account_popup is not None and self._account_popup.winfo_exists():
            self._close_account_popup()  # Reopened fresh next time to show the new state

    # ---------- Google-style account menu ----------

    def _account_action(self):
        if self._account_popup is not None and self._account_popup.winfo_exists():
            self._close_account_popup()
        else:
            self._open_account_popup()

    def _close_account_popup(self):
        if self._account_popup is not None:
            self.unbind_all("<Button-1>")
            try:
                self._account_popup.destroy()
            except tk.TclError:
                pass
            self._account_popup = None

    def _open_account_popup(self):
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER, width=300)
        card.place(x=14, rely=1.0, y=-62, anchor="sw")
        self._account_popup = card
        self._fill_account_popup(card)
        # Close when the next click lands outside the card and the avatar
        self.after(10, lambda: self.bind_all("<Button-1>", self._maybe_close_account, add="+"))

    def _maybe_close_account(self, event):
        widget = event.widget
        while widget is not None:
            if widget is self._account_popup or widget is self.btn_account:
                return
            widget = getattr(widget, "master", None)
        self._close_account_popup()

    def _fill_account_popup(self, card):
        logged_in = bool(self.services.zipzap.session)
        email = self.services.config.get("zipzap_email") if logged_in else ""
        name = email.split("@")[0] if email else ""

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(18, 12))
        circle = ctk.CTkFrame(header, width=48, height=48, corner_radius=24,
                              fg_color=ACCENT_PRIMARY if logged_in else BG_HOVER)
        circle.pack(side="left", padx=(0, 14))
        circle.pack_propagate(False)
        if logged_in:
            ctk.CTkLabel(circle, text=name[:1].upper(), font=font(20, "bold"), text_color="#FFFFFF").pack(expand=True)
        else:
            ctk.CTkLabel(circle, text="", image=create_icon_image(Icons.PERSON, TEXT_MUTED, 24)).pack(expand=True)
        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(info, text=(name or "ZipZap AI"), font=font(15, "bold"),
                     text_color=TEXT_MAIN, anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=(email or "ยังไม่ได้ login"), font=font(12),
                     text_color=TEXT_MUTED, anchor="w").pack(anchor="w")

        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x")
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(12, 16))
        if logged_in:
            self._popup_usage = ctk.CTkLabel(body, text="กำลังตรวจโควตาวันนี้...", font=font(12, "bold"),
                                             text_color=TEXT_MUTED, anchor="w")
            self._popup_usage.pack(anchor="w", pady=(0, 12))
            ctk.CTkButton(body, text="Logout", command=self._popup_logout, height=36, width=240,
                          fg_color=BG_HOVER, hover_color=BORDER, text_color=TEXT_MAIN).pack(fill="x")
            self.run_background(self.services.zipzap.usage, on_done=self._popup_show_usage)
        else:
            ctk.CTkLabel(body, text="login ด้วยบัญชี Google เพื่อใช้ AI ของทีมได้ฟรี วันละ 50 ครั้ง",
                         font=font(12), text_color=TEXT_MUTED, wraplength=240, justify="left",
                         anchor="w").pack(anchor="w", pady=(0, 12))
            ctk.CTkButton(body, text="Login ด้วย Google", command=self._popup_login, height=38, width=240,
                          fg_color=ACCENT_PRIMARY, hover_color=ACCENT_HOVER).pack(fill="x")

    def _popup_show_usage(self, usage):
        lbl = getattr(self, "_popup_usage", None)
        if lbl is None:
            return
        if usage is None:
            text, color = "⚠️ ติดต่อ server ไม่ได้", WARNING_COLOR
        elif usage.get("expired"):
            text, color = "⚠️ login หมดอายุ กรุณา login ใหม่", WARNING_COLOR
        elif usage.get("remaining", 0) <= 0:
            text, color = f"⚠️ ใช้ครบ {usage['limit']} ครั้งของวันนี้แล้ว", WARNING_COLOR
        else:
            text, color = f"วันนี้ใช้ไป {usage['used']}/{usage['limit']} ครั้ง", ACCENT_SUCCESS
        try:
            lbl.configure(text=text, text_color=color)
        except tk.TclError:
            pass  # The popup was closed before usage came back

    def _popup_login(self):
        self._close_account_popup()
        self.show_page("settings")
        self.pages["settings"]._toggle_login()

    def _popup_logout(self):
        self._close_account_popup()
        self.pages["settings"]._toggle_login()  # Logs out when a session exists

    def _toggle_theme(self):
        theme = "Dark" if self.switch_theme.get() == 1 else "Light"
        self.services.config.set("theme", theme)
        ctk.set_appearance_mode(theme)
        self.pages["dashboard"].refresh_stats()  # The donut is a bitmap: redraw it in the new colours

    def _on_close(self):
        self.services.watcher.stop_watching()
        self.destroy()
