from flask import Blueprint, request
from controller.product import create, read, delete, update_multi, show
from controller.access import check_permission

products = Blueprint("products", __name__)


@products.route("", methods=["POST"])
@check_permission('product.create')
def create_product():
    data = request.get_json()

    return create(data)


@products.route("/search", methods=["POST"])
@check_permission('product.read')
def read_product():

    return read()


@products.route("/edit", methods=["PATCH"])
@check_permission('product.edit')
def edit_product():
    data = request.get_json()

    return update_multi(data)


@products.route("/delete", methods=["DELETE"])
@check_permission('product.delete')
def delete_product():
    data = request.get_json()

    return delete(data)


@products.route("/<int:product_id>", methods=["GET"])
@check_permission('product.read')
def show_product(product_id):

    return show(product_id)
