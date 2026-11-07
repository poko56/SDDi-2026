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
