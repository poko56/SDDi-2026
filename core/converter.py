import os

from PIL import Image
from pillow_heif import register_heif_opener

from core.paths import unique_path

register_heif_opener()

SAME_AS_SOURCE = None


class FileConverter:
    """Image, document and media conversions.

    Each UI mode maps target formats to a handler in `_registry()`, so adding a
    conversion means adding one entry there; the UI builds its menus from it.
    """

    def __init__(self, logger):
        self.logger = logger

    def _registry(self):
        return {
            "Image": {
                "filetypes": [("Image Files", "*.jpg *.jpeg *.png *.heic *.webp *.bmp")],
                "targets": {
                    ".jpg": lambda p, out: self.convert_image(p, "JPEG", out),
                    ".png": lambda p, out: self.convert_image(p, "PNG", out),
                    "Compress (Keep format)": lambda p, out: self.compress_image(p, 5, out),
                },
            },
        }

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

    def convert_image(self, input_path, output_format="JPEG", output_dir=SAME_AS_SOURCE):
        """Convert an image (including HEIC/WEBP) to JPEG or PNG."""
        if not os.path.exists(input_path):
            return False, "ไม่พบไฟล์ต้นฉบับ"
        is_jpeg = output_format.upper() in ("JPEG", "JPG")
        output_path = self._output_path(input_path, output_dir, ".jpg" if is_jpeg else ".png")
        try:
            with Image.open(input_path) as img:
                if is_jpeg and img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                img.save(output_path, format="JPEG" if is_jpeg else "PNG")
        except (OSError, ValueError) as e:
            return False, f"แปลงรูปภาพไม่สำเร็จ: {e}"
        self.logger.log_action("CONVERT_IMAGE", f"Converted {os.path.basename(input_path)} to {output_path}")
        return True, output_path

    def compress_image(self, input_path, max_size_mb=5, output_dir=SAME_AS_SOURCE):
        """Re-save images larger than max_size_mb as quality-75 JPEG."""
        try:
            size_mb = os.path.getsize(input_path) / (1024 * 1024)
            if size_mb <= max_size_mb:
                return True, "ไฟล์มีขนาดเล็กกว่าขีดจำกัดอยู่แล้ว"
            output_path = self._output_path(input_path, output_dir, "_compressed.jpg")
            with Image.open(input_path) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(output_path, "JPEG", quality=75, optimize=True)
        except (OSError, ValueError) as e:
            return False, f"บีบอัดรูปภาพไม่สำเร็จ: {e}"
        self.logger.log_action("COMPRESS_IMAGE", f"Compressed {os.path.basename(input_path)} (was {size_mb:.2f}MB)")
        return True, output_path
