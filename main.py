"""ZipZap entry point: build the services, then start the window."""
from core.services import build_services
from ui.app import ZipZapApp


def main():
    app = ZipZapApp(build_services())
    app.mainloop()


if __name__ == "__main__":
    main()
