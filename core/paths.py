"""Where ZipZap reads bundled resources and writes user data."""
import os
import sys

APP_DIR_NAME = ".zipzap"
TRASH_DIR_NAME = ".zipzap_trash"


def is_frozen():
    """True when running from a PyInstaller build."""
    return getattr(sys, "frozen", False)


def resource_dir():
    """Folder holding icon.png, assets/ etc. (the PyInstaller bundle or the source tree)."""
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts):
    return os.path.join(resource_dir(), *parts)


def user_data_dir():
    """Per-user folder for config and logs.

    A packaged app's working directory is not writable (it is "/" on macOS),
    so nothing may be written relative to the CWD.
    """
    path = os.path.join(os.path.expanduser("~"), APP_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def user_data_path(name):
    return os.path.join(user_data_dir(), name)
