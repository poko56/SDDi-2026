from PIL import Image

from conftest import write
from core.converter import FileConverter


def test_convert_png_with_alpha_to_jpg(logger, workdir):
    src = workdir / "logo.png"
    Image.new("RGBA", (20, 20), (255, 0, 0, 128)).save(src)

    ok, out = FileConverter(logger).convert_image(str(src), "JPEG")

    assert ok
    assert out.endswith("logo.jpg")
    assert Image.open(out).format == "JPEG"


def test_convert_image_to_custom_output_dir(logger, workdir, tmp_path):
    src = workdir / "a.jpg"
    Image.new("RGB", (20, 20)).save(src)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    ok, out = FileConverter(logger).convert_image(str(src), "PNG", output_dir=str(out_dir))

    assert ok
    assert (out_dir / "a.png").exists()


def test_convert_image_missing_file(logger, workdir):
    ok, _ = FileConverter(logger).convert_image(str(workdir / "nope.png"))
    assert not ok


def test_convert_image_rejects_non_image(logger, workdir):
    src = write(workdir / "fake.png", "not an image")
    ok, _ = FileConverter(logger).convert_image(str(src))
    assert not ok


def test_compress_skips_small_image(logger, workdir):
    src = workdir / "small.jpg"
    Image.new("RGB", (10, 10)).save(src)

    ok, msg = FileConverter(logger).compress_image(str(src), max_size_mb=5)

    assert ok
    assert not (workdir / "small_compressed.jpg").exists()


def test_compress_large_image(logger, workdir):
    src = workdir / "big.png"
    Image.effect_noise((600, 600), 100).convert("RGB").save(src)

    ok, out = FileConverter(logger).compress_image(str(src), max_size_mb=0.1)

    assert ok
    assert out.endswith("big_compressed.jpg")


def test_docx_to_pdf_rejects_other_types(logger, workdir):
    ok, _ = FileConverter(logger).convert_docx_to_pdf(str(write(workdir / "a.txt")))
    assert not ok


def test_extract_audio_rejects_non_video(logger, workdir):
    ok, _ = FileConverter(logger).extract_audio(str(write(workdir / "a.txt")))
    assert not ok


def test_registry_drives_modes_and_targets(logger):
    converter = FileConverter(logger)
    assert converter.modes() == ["Document", "Image", "Media"]
    assert converter.targets_for("Image") == [".jpg", ".png", "Compress (Keep format)"]
    assert converter.filetypes_for("Media")[-1] == ("All Files", "*.*")


def test_convert_dispatches_to_registered_handler(logger, workdir):
    src = workdir / "a.png"
    Image.new("RGB", (5, 5)).save(src)

    ok, out = FileConverter(logger).convert(str(src), "Image", ".jpg")

    assert ok
    assert out.endswith("a.jpg")


def test_convert_unknown_combination(logger, workdir):
    ok, msg = FileConverter(logger).convert(str(workdir / "a.png"), "Image", ".gif")
    assert not ok
    assert ".gif" in msg


def test_convert_never_overwrites_existing_output(logger, workdir):
    Image.new("RGB", (5, 5), "blue").save(workdir / "photo.png")
    Image.new("RGB", (5, 5), "green").save(workdir / "photo.jpg")

    ok, out = FileConverter(logger).convert_image(str(workdir / "photo.png"), "JPEG")

    assert ok
    assert out.endswith("photo_1.jpg")
    assert Image.open(workdir / "photo.jpg").getpixel((1, 1))[1] > 100  # Still the green original


def test_convert_same_format_keeps_source(logger, workdir):
    src = workdir / "a.png"
    Image.new("RGB", (5, 5)).save(src)
    before = src.read_bytes()

    ok, out = FileConverter(logger).convert_image(str(src), "PNG")

    assert ok
    assert out.endswith("a_1.png")
    assert src.read_bytes() == before
