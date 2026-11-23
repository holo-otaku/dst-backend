from flask_smorest import Blueprint
from marshmallow import Schema, fields

from controller.log import read_multi, user_logs
from controller.access import check_permission
from routers.schemas import Message, Paging, errors

log = Blueprint("Log", __name__, description="操作紀錄")


class LogRow(Schema):
    url = fields.String()
    method = fields.String()
    payload = fields.String(metadata={"description": "超過 50 字會截斷"})
    userName = fields.String(allow_none=True)
    status = fields.Integer(allow_none=True, metadata={"description": "HTTP 狀態碼，舊紀錄為空"})
    ip = fields.String(allow_none=True)
    userAgent = fields.String(allow_none=True)
    createdAt = fields.String(metadata={"example": "2025-01-01 12:00:00"})


class LogListResponse(Message):
    data = fields.List(fields.Nested(LogRow))
    totalCount = fields.Integer()


class UserLogRow(Schema):
    id = fields.Integer()
    url = fields.String()
    userId = fields.Integer()
    payload = fields.Raw()
    status = fields.Integer(allow_none=True, metadata={"description": "HTTP 狀態碼，舊紀錄為空"})
    ip = fields.String(allow_none=True)
    userAgent = fields.String(allow_none=True)
    createdAt = fields.String(metadata={"example": "2025-01-01 12:00:00"})


class UserLogResponse(Message):
    data = fields.List(fields.Nested(UserLogRow))


@log.route("", methods=["GET"])
@check_permission('log.read')
@log.arguments(Paging, location="query")
@log.response(200, LogListResponse)
@errors(log, 403)
def get_logs(_query):
    """所有操作紀錄，新的在前（含登入成功/失敗、被權限擋下的請求）"""
    return read_multi()


@log.route('/user/<int:user_id>', methods=['GET'])
@check_permission('log.read')
@log.arguments(Paging, location="query")
@log.response(200, UserLogResponse)
@errors(log, 403)
def get_user_logs(_query, user_id):
    """指定使用者的操作紀錄"""
    return user_logs(user_id)
