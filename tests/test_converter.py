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
