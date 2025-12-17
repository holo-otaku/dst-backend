from flask import Blueprint, request
from controller.user import create, read, read_multi, update, force_logout, force_logout_all
from controller.access import check_permission

user = Blueprint("user", __name__)


@user.route("", methods=["GET"])
@check_permission('user.read')
def get_users():
    return read_multi()


@user.route("/<int:user_id>", methods=["GET"])
@check_permission('user.read')
def get_user(user_id):

    return read(user_id)


@user.route("", methods=["POST"])
@check_permission('user.create')
def create_user():
    data = request.get_json()

    return create(data)


@user.route("<int:user_id>", methods=["PATCH"])
@check_permission('user.edit')
def update_user(user_id):
    data = request.get_json()

    return update(user_id, data)


@user.route("<int:user_id>/force-logout", methods=["POST"])
@check_permission('user.edit')
def force_logout_user(user_id):
    """強制指定使用者登出"""
    return force_logout(user_id)


@user.route("/force-logout-all", methods=["POST"])
@check_permission('user.edit')
def force_logout_all_users():
    """強制所有使用者登出"""
    return force_logout_all()


# 保留 DELETE 路由以向後相容，但實際上執行停用操作
@user.route("<int:user_id>", methods=["DELETE"])
@check_permission('user.delete')
def delete_user(user_id):
    """停用使用者（向後相容）"""
    return update(user_id, {'isDisabled': True})
