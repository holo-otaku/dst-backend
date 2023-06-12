from flask import Blueprint, request
from controller.product import create, read, edit, delete
from flask_jwt_extended import jwt_required

products = Blueprint("products", __name__)


@products.route("", methods=["POST"])
@jwt_required()
def create_product():
    data = request.get_json()

    return create(data)


@products.route("/<int:series_id>/search", methods=["POST"])
@jwt_required()
def read_product(series_id):

    return read(series_id)


@products.route("/edit", methods=["PUT"])
@jwt_required()
def edit_product():
    data = request.get_json()

    return edit(data)

@products.route("/delete", methods=["DELETE"])
@jwt_required()
def delete_product():
    data = request.get_json()

    return delete(data)