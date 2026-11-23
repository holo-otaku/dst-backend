from flask_smorest import Blueprint
from marshmallow import Schema, fields

from controller.user import create, read, read_multi, update, force_logout, force_logout_all
from controller.access import check_permission
from routers.schemas import Body, Message, Paging, errors

user = Blueprint("User", __name__, description="使用者")


class UserQuery(Paging):
    all = fields.Boolean(metadata={"description": "true 時包含已停用的使用者"})


class UserCreate(Body):
    username = fields.String(required=True)
    password = fields.String(required=True)
    roleId = fields.Integer(required=True)


class UserUpdate(Body):
    username = fields.String(allow_none=True)
    password = fields.String(allow_none=True, metadata={"description": "改密碼會讓舊 token 失效"})
    roleId = fields.Integer(allow_none=True, metadata={"description": "換角色會讓舊 token 失效"})
    isDisabled = fields.Boolean(allow_none=True)


class UserRow(Schema):
    id = fields.Integer()
    userName = fields.String()
    role = fields.String(allow_none=True)
    isDisabled = fields.Boolean()


class UserListResponse(Message):
    data = fields.List(fields.Nested(UserRow))
    totalCount = fields.Integer()


class UserDetail(Schema):
    userName = fields.String()
    role = fields.String(allow_none=True)
    roleId = fields.Integer(allow_none=True)


class UserDetailResponse(Message):
    data = fields.Nested(UserDetail)


class UserSaved(Schema):
    id = fields.Integer()
    username = fields.String()
    role = fields.String()
    isDisabled = fields.Boolean()


class UserSavedResponse(Message):
    data = fields.Nested(UserSaved)


class ForceLogout(Schema):
    userId = fields.Integer()
    tokenVersion = fields.Integer()


class ForceLogoutResponse(Message):
    data = fields.Nested(ForceLogout)


# check_permission 放在最外層：沒權限先回 403，不先驗證 body
@user.route("", methods=["GET"])
@check_permission('user.read')
@user.arguments(UserQuery, location="query")
@user.response(200, UserListResponse)
@errors(user, 403)
def get_users(_query):
    """使用者列表"""
    return read_multi()


@user.route("/<int:user_id>", methods=["GET"])
@check_permission('user.read')
@user.response(200, UserDetailResponse)
@errors(user, 403, 404)
def get_user(user_id):
    """取得使用者（已停用的視為不存在）"""
    return read(user_id)


@user.route("", methods=["POST"])
@check_permission('user.create')
@user.arguments(UserCreate)
@user.response(201, UserSavedResponse)
@errors(user, 400, 403)
def create_user(data):
    """新增使用者，只能指派自己權限範圍內的角色"""
    return create(data)


@user.route("<int:user_id>", methods=["PATCH"])
@check_permission('user.edit')
@user.arguments(UserUpdate)
@user.response(200, UserSavedResponse)
@errors(user, 400, 403, 404)
def update_user(data, user_id):
    """編輯使用者，只送要改的欄位"""
    return update(user_id, data)


@user.route("<int:user_id>/force-logout", methods=["POST"])
@check_permission('user.edit')
@user.response(200, ForceLogoutResponse)
@errors(user, 403, 404)
def force_logout_user(user_id):
    """強制指定使用者登出"""
    return force_logout(user_id)


@user.route("/force-logout-all", methods=["POST"])
@check_permission('user.edit')
@user.response(200, Message)
@errors(user, 403)
def force_logout_all_users():
    """強制所有使用者登出"""
    return force_logout_all()


# 保留 DELETE 路由以向後相容，但實際上執行停用操作
@user.route("<int:user_id>", methods=["DELETE"])
@check_permission('user.delete')
@user.response(200, UserSavedResponse)
@errors(user, 403, 404)
def delete_user(user_id):
    """停用使用者（向後相容）"""
    return update(user_id, {'isDisabled': True})
