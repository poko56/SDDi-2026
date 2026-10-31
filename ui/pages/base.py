import customtkinter as ctk


class BasePage(ctk.CTkFrame):
    """A screen shown in the main content area. Subclasses build their widgets in build()."""

    title = ""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.services = app.services
        self.build()

    def build(self):
        raise NotImplementedError

    def on_show(self):
        """Called every time the page becomes visible."""
