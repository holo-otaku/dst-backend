from flask import Blueprint, request
from controller.role import create, read, update, delete, read_multi
from controller.access import check_permission

role = Blueprint("role", __name__)


@role.route("", methods=["GET"])
@check_permission('role.read')
def get_roles():

    return read_multi()


@role.route("/<int:role_id>", methods=["GET"])
@check_permission('role.read')
def get_role(role_id):

    return read(role_id)


@role.route("", methods=["POST"])
@check_permission('role.create')
def create_role():
    data = request.get_json()

    return create(data)


@role.route("<int:role_id>", methods=["PATCH"])
@check_permission('role.edit')
def update_role(role_id):
    data = request.get_json()

    return update(role_id, data)


@role.route("<int:role_id>", methods=["DELETE"])
@check_permission('role.delete')
def delete_role(role_id):

    return delete(role_id)
