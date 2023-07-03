from flask import Blueprint, request
from controller.user import create, read, read_multi, update, delete
from controller.access import check_permission

user = Blueprint("user", __name__)


@user.route("/multi", methods=["GET"])
@check_permission('read')
def get_users():

    return read_multi()


@user.route("/<int:user_id>", methods=["GET"])
@check_permission('read')
def get_user(user_id):

    return read(user_id)


@user.route("", methods=["POST"])
@check_permission('create')
def create_user():
    data = request.get_json()

    return create(data)


@user.route("<int:user_id>", methods=["PATCH"])
@check_permission('edit')
def update_user(user_id):
    data = request.get_json()

    return update(user_id, data)


@user.route("<int:user_id>", methods=["DELETE"])
@check_permission('delete')
def delete_user(user_id):

    return delete(user_id)
