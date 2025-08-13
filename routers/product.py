from flask import Blueprint, request
from controller.product import (
    create,
    read,
    delete,
    update_multi,
    read_multi,
    export_excel,
    create_from_items,
)
from controller.access import check_permission

products = Blueprint("products", __name__)


@products.route("", methods=["POST"])
@check_permission("product.create")
def create_product():
    data = request.get_json()

    return create(data)


@products.route("/copy", methods=["POST"])
@check_permission("product.create")
def copy_product():
    data = request.get_json()

    return create_from_items(data)


@products.route("/search", methods=["POST"])
@check_permission("product.read")
def read_multi_product():
    data = request.get_json()

    return read_multi(data)


@products.route("/export", methods=["POST"])
@check_permission("product.read")
def export_product():
    data = request.get_json()

    return export_excel(data)


@products.route("/edit", methods=["PATCH"])
@check_permission("product.edit")
def edit_product():
    data = request.get_json()

    return update_multi(data)


@products.route("/delete", methods=["DELETE"])
@check_permission("product.delete")
def delete_product():
    data = request.get_json()

    return delete(data)


@products.route("/<int:product_id>", methods=["GET"])
@check_permission("product.read")
def read_product(product_id):

    return read(product_id)
