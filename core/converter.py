import os

from core.paths import unique_path

SAME_AS_SOURCE = None


class FileConverter:
    """Image, document and media conversions.

    Each UI mode maps target formats to a handler in `_registry()`, so adding a
    conversion means adding one entry there; the UI builds its menus from it.
    """

    def __init__(self, logger):
        self.logger = logger

    def _registry(self):
        return {}

    def modes(self):
        return list(self._registry())

    def targets_for(self, mode):
        return list(self._registry()[mode]["targets"])

    def filetypes_for(self, mode):
        return self._registry()[mode]["filetypes"] + [("All Files", "*.*")]

    def convert(self, input_path, mode, target, output_dir=SAME_AS_SOURCE):
        """Run the conversion registered for (mode, target). Returns (ok, output_path_or_error)."""
        handler = self._registry().get(mode, {}).get("targets", {}).get(target)
        if handler is None:
            return False, f"ไม่รองรับการแปลงแบบ {mode} → {target}"
        return handler(input_path, output_dir)

    @staticmethod
    def _output_path(input_path, output_dir, suffix):
        """Where to write the result; never an existing file (including the source itself)."""
        stem = os.path.splitext(os.path.basename(input_path))[0]
        return unique_path(os.path.join(output_dir or os.path.dirname(input_path), stem + suffix))
