import io
import pytest
from PIL import Image as PILImage
from .client import app
from controller.image import create, read
from models.image import Image
from models.shared import db


def test_create_saves_file_and_path(app, tmp_path):
    app.config["IMG_PATH"] = str(tmp_path)
    png = io.BytesIO()
    PILImage.new("RGB", (4, 4), "red").save(png, "PNG")

    with app.test_request_context(
        method="POST", data={"image_data": (io.BytesIO(png.getvalue()), "a.png")}
    ):
        response = create()
        image = db.session.get(Image, response.get_json()["image_id"])

    assert response.status_code == 201
    assert image.path.startswith(str(tmp_path))
    with open(image.path, "rb") as f:
        assert f.read() == png.getvalue()


def test_create_rejects_non_image(app, tmp_path):
    app.config["IMG_PATH"] = str(tmp_path)

    with app.test_request_context(
        method="POST", data={"image_data": (io.BytesIO(b"not an image"), "a.png")}
    ):
        response = create()
        assert db.session.query(Image).count() == 0

    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


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
