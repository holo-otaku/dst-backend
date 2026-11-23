from flask_smorest import Blueprint
from marshmallow import Schema, fields

from controller.permission import create, read, update, delete, read_multi
from controller.access import check_permission
from routers.schemas import Body, Message, Paging, errors

permission = Blueprint("Permission", __name__, description="權限")


class PermissionCreate(Body):
    name = fields.String(required=True, metadata={"example": "product.read"})


class PermissionUpdate(Body):
    name = fields.String(metadata={"description": "改名需要持有全部權限"})


class PermissionOut(Schema):
    id = fields.Integer()
    name = fields.String()


class PermissionResponse(Message):
    data = fields.Nested(PermissionOut)


class PermissionListResponse(Message):
    data = fields.List(fields.Nested(PermissionOut))
    totalCount = fields.Integer()


# check_permission 放在最外層：沒權限先回 403，不先驗證 body
@permission.route("", methods=["GET"])
@check_permission('permission.read')
@permission.arguments(Paging, location="query")
@permission.response(200, PermissionListResponse)
@errors(permission, 403)
def get_permissions(_query):
    """權限列表"""
    return read_multi()


@permission.route("/<int:permission_id>", methods=["GET"])
@check_permission('permission.read')
@permission.response(200, PermissionResponse)
@errors(permission, 403, 404)
def get_permission(permission_id):
    """取得權限"""
    return read(permission_id)


@permission.route("", methods=["POST"])
@check_permission('permission.create')
@permission.arguments(PermissionCreate)
@permission.response(200, PermissionResponse)
@errors(permission, 400, 403)
def create_permission(data):
    """新增權限"""
    return create(data)


@permission.route("<int:permission_id>", methods=["PATCH"])
@check_permission('permission.edit')
@permission.arguments(PermissionUpdate)
@permission.response(200, Message)
@errors(permission, 403, 404)
def update_permission(data, permission_id):
    """權限改名，會讓持有者重新登入"""
    return update(permission_id, data)


@permission.route("<int:permission_id>", methods=["DELETE"])
@check_permission('permission.delete')
@permission.response(200, Message)
@errors(permission, 403, 404)
def delete_permission(permission_id):
    """刪除權限"""
    return delete(permission_id)
