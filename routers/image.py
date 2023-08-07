from flask import Blueprint
from controller.image import read, create
from controller.access import check_permission

image = Blueprint("image", __name__)


@image.route("/<int:image_id>", methods=["GET"])
# @check_permission('image.read')
def get_image(image_id):

    return read(image_id)


@image.route("", methods=["POST"])
@check_permission('image.create')
def create_image():

    return create()
