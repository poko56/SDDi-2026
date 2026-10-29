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


def safe_join(root, rel_path):
    """Join an untrusted relative path (e.g. one the AI wrote) onto root.

    Returns None if the result would escape root via "..", an absolute path or a symlink.
    """
    if not root or not rel_path:
        return None
    real_root = os.path.realpath(root)
    full = os.path.realpath(os.path.join(real_root, rel_path))
    try:
        if os.path.commonpath([real_root, full]) != real_root:
            return None
    except ValueError:
        return None
    return full


def unique_path(path):
    """Return path, or path with _1, _2 ... before the extension if that name is taken."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"
