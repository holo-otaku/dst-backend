from flask_smorest import Blueprint
from marshmallow import Schema, fields

from controller.image import read, create
from controller.access import check_permission
from routers.schemas import Message, errors

image = Blueprint("Image", __name__, description="圖片")


class ImageUpload(Schema):
    image_data = fields.Raw(required=True, metadata={"type": "string", "format": "binary"})


class ImageCreatedResponse(Message):
    image_id = fields.Integer()


@image.route("/<int:image_id>", methods=["GET"])
@check_permission('product.read')
@image.response(200, content_type="application/octet-stream", description="圖片檔（png 或 jpg）")
@errors(image, 403, 404)
def get_image(image_id):
    """下載圖片，limit 欄位的圖片需要 limit-field.read"""
    return read(image_id)


@image.route("", methods=["POST"])
@check_permission('image.create')
@image.arguments(ImageUpload, location="files")
@image.response(201, ImageCreatedResponse)
@errors(image, 400, 403)
def create_image(_files):
    """上傳圖片"""
    return create()
