import os


class ExclusionPolicy:
    """Folders the user asked ZipZap never to touch.

    One instance is shared by the cleaner, organizer and watcher, so a change
    made in Settings applies everywhere at once.
    """

    def __init__(self, folders=None):
        self._folders = []
        self.update(folders or [])

    @property
    def folders(self):
        return list(self._folders)

    def update(self, folders):
        self._folders = [os.path.abspath(f) for f in folders if f]

    def is_excluded(self, path):
        abs_path = os.path.abspath(path)
        for folder in self._folders:
            try:
                if os.path.commonpath([abs_path, folder]) == folder:
                    return True
            except ValueError:
                # Different drives on Windows: cannot be inside each other
                continue
        return False
