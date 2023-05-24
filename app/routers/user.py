from flask import Blueprint, request
from controller.user import create, read, read_multi, update, delete
from flask_jwt_extended import jwt_required

user = Blueprint("user", __name__)


@user.route("", methods=["GET"])
# @jwt_required()
def get_users():

    return read_multi()


@user.route("/<int:user_id>", methods=["GET"])
# @jwt_required()
def get_user(user_id):

    return read(user_id)


@user.route("", methods=["POST"])
# @jwt_required()
def create_user():
    data = request.get_json()

    return create(data)


@user.route("<int:user_id>", methods=["PATCH"])
# @jwt_required()
def update_user(user_id):
    data = request.get_json()

    return update(user_id, data)


@user.route("<int:user_id>", methods=["DELETE"])
# @jwt_required()
def delete_user(user_id):

    return delete(user_id)
