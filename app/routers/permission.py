from flask import Blueprint, request
from controller.permission import create, read, update, delete, read_multi
from flask_jwt_extended import jwt_required

permission = Blueprint("permission", __name__)


@permission.route("", methods=["GET"])
@jwt_required()
def get_permissions():

    return read_multi()


@permission.route("/<int:permission_id>", methods=["GET"])
@jwt_required()
def get_permission(permission_id):

    return read(permission_id)


@permission.route("", methods=["POST"])
@jwt_required()
def create_permission():
    data = request.get_json()

    return create(data)


@permission.route("<int:permission_id>", methods=["PATCH"])
@jwt_required()
def update_permission(permission_id):
    data = request.get_json()

    return update(permission_id, data)


@permission.route("<int:permission_id>", methods=["DELETE"])
@jwt_required()
def delete_permission(permission_id):

    return delete(permission_id)
