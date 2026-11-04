from tkinter import filedialog

import customtkinter as ctk

from core.file_types import format_size
from ui.pages.base import BasePage
from ui.theme import (ACCENT_HOVER, ACCENT_PRIMARY, CHART_DOCUMENTS, CHART_EMPTY, CHART_MEDIA, CHART_OTHERS,
                      TEXT_MAIN, TEXT_MUTED, font)
from ui.widgets import card, render_donut


class DashboardPage(BasePage):
    title = "Dashboard"

    def build(self):
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 20))
        self._build_storage_card(top_row)
        self._build_folder_card(top_row)

        self.app.on_folder_change(self._on_folder_changed)
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

    # ---------- Behaviour ----------

    def _select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.app.set_folder(folder)

    def _on_folder_changed(self, folder):
        self.lbl_folder.configure(text=folder)
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
