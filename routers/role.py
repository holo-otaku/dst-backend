from flask_smorest import Blueprint
from marshmallow import Schema, fields

from controller.role import create, read, update, delete, read_multi
from controller.access import check_permission
from routers.schemas import Body, Message, Paging, errors

role = Blueprint("Role", __name__, description="角色")


class RoleBody(Body):
    roleName = fields.String(required=True)
    permissionIds = fields.List(fields.Integer(), required=True)


class PermissionRef(Schema):
    id = fields.Integer()
    name = fields.String()


class RoleOut(Schema):
    id = fields.Integer()
    name = fields.String()
    permissions = fields.List(fields.Nested(PermissionRef))


class RoleResponse(Message):
    data = fields.Nested(RoleOut)


class RoleListResponse(Message):
    data = fields.List(fields.Nested(RoleOut))
    totalCount = fields.Integer()


class RoleId(Schema):
    id = fields.Integer()


class RoleCreatedResponse(Message):
    data = fields.Nested(RoleId)


# check_permission 放在最外層：沒權限先回 403，不先驗證 body
@role.route("", methods=["GET"])
@check_permission('role.read')
@role.arguments(Paging, location="query")
@role.response(200, RoleListResponse)
@errors(role, 403)
def get_roles(_query):
    """角色列表"""
    return read_multi()


@role.route("/<int:role_id>", methods=["GET"])
@check_permission('role.read')
@role.response(200, RoleResponse)
@errors(role, 403, 404)
def get_role(role_id):
    """取得角色與權限"""
    return read(role_id)


@role.route("", methods=["POST"])
@check_permission('role.create')
@role.arguments(RoleBody)
@role.response(201, RoleCreatedResponse)
@errors(role, 400, 403)
def create_role(data):
    """新增角色，只能授予自己有的權限"""
    return create(data)


@role.route("<int:role_id>", methods=["PATCH"])
@check_permission('role.edit')
@role.arguments(RoleBody)
@role.response(200, Message)
@errors(role, 400, 403, 404)
def update_role(data, role_id):
    """編輯角色，會讓擁有此角色的使用者重新登入"""
    return update(role_id, data)


@role.route("<int:role_id>", methods=["DELETE"])
@check_permission('role.delete')
@role.response(200, Message)
@errors(role, 403, 404)
def delete_role(role_id):
    """刪除角色"""
    return delete(role_id)
