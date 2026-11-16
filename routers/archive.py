from flask_smorest import Blueprint
from marshmallow import Schema, fields

from controller.archive import create, delete
from controller.access import check_permission
from routers.schemas import ItemIds, Message, errors

archive = Blueprint("Archive", __name__, description="產品封存")


class Skipped(Schema):
    skipped = fields.List(fields.Integer(), metadata={"description": "已經封存過的"})


class ArchiveResponse(Message):
    data = fields.Nested(Skipped)


class Unarchived(Schema):
    deleted = fields.List(fields.Integer())
    notFound = fields.List(fields.Integer())


class UnarchiveResponse(Message):
    data = fields.Nested(Unarchived)


# check_permission 放在最外層：沒權限先回 403，不先驗證 body
@archive.route("", methods=["POST"])
@check_permission("archive.create")
@archive.arguments(ItemIds)
@archive.response(200, ArchiveResponse)
@errors(archive, 400, 403)
def create_archive(data):
    """封存產品"""
    return create(data)


@archive.route("", methods=["DELETE"])
@check_permission("archive.delete")
@archive.arguments(ItemIds)
@archive.response(200, UnarchiveResponse)
@errors(archive, 400, 403)
def delete_archive(data):
    """取消封存"""
    return delete(data)
