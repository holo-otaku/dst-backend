from flask import Blueprint, request
from controller.permission import create, read, update, delete, read_multi
from controller.access import check_permission

permission = Blueprint("permission", __name__)


@permission.route("", methods=["GET"])
@check_permission('permission.read')
def get_permissions():

    return read_multi()


@permission.route("/<int:permission_id>", methods=["GET"])
@check_permission('permission.read')
def get_permission(permission_id):

    return read(permission_id)


@permission.route("", methods=["POST"])
@check_permission('permission.create')
def create_permission():
    data = request.get_json()

    return create(data)


@permission.route("<int:permission_id>", methods=["PATCH"])
@check_permission('permission.edit')
def update_permission(permission_id):
    data = request.get_json()

    return update(permission_id, data)


@permission.route("<int:permission_id>", methods=["DELETE"])
@check_permission('permission.delete')
def delete_permission(permission_id):

    return delete(permission_id)
