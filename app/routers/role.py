from flask import Blueprint, request
from controller.role import create, read, update, delete, read_multi
from flask_jwt_extended import jwt_required

role = Blueprint("role", __name__)


@role.route("", methods=["GET"])
# @jwt_required()
def get_roles():

    return read_multi()


@role.route("/<int:role_id>", methods=["GET"])
# @jwt_required()
def get_role(role_id):

    return read(role_id)


@role.route("", methods=["POST"])
# @jwt_required()
def create_role():
    data = request.get_json()

    return create(data)


@role.route("<int:role_id>", methods=["PATCH"])
# @jwt_required()
def update_role(role_id):
    data = request.get_json()

    return update(role_id, data)


@role.route("<int:role_id>", methods=["DELETE"])
# @jwt_required()
def delete_role(role_id):

    return delete(role_id)
