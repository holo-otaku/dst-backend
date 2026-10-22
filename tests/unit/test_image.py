import pytest
from PIL import Image as PILImage
from .client import app
from controller.image import read
from models.image import Image
from models.shared import db


@pytest.mark.parametrize(
    "image_format, mimetype, extension",
    [("PNG", "image/png", "png"), ("JPEG", "image/jpeg", "jpg")],
)
def test_read_detects_real_format(app, tmp_path, image_format, mimetype, extension):
    # Files are always named .png regardless of the uploaded format
    path = tmp_path / "image_1_1.png"
    PILImage.new("RGB", (4, 4), "red").save(path, image_format)

    with app.test_request_context():
        db.session.add(Image(id=1, name="test", path=str(path)))
        db.session.commit()

        response = read(1)

    assert response.status_code == 200
    assert response.mimetype == mimetype
    assert f'filename=1.{extension}' in response.headers["Content-Disposition"]
    response.close()


def test_read_unknown_format_falls_back_to_octet_stream(app, tmp_path):
    path = tmp_path / "image_1_1.png"
    path.write_bytes(b"not an image")

    with app.test_request_context():
        db.session.add(Image(id=1, name="test", path=str(path)))
        db.session.commit()

        response = read(1)

    assert response.status_code == 200
    assert response.mimetype == "application/octet-stream"
    response.close()
