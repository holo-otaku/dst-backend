from flask import jsonify
from flask_smorest import Blueprint
from marshmallow import Schema, fields

from controller.field import search_item_attribute_by_field_id_and_value
from controller.access import check_permission
from routers.schemas import Message, errors

field = Blueprint("Field", __name__, description="欄位值")


class FieldSearchQuery(Schema):
    field_id = fields.Integer(required=True)
    search_value = fields.String(metadata={"description": "模糊搜尋，空白時回傳全部（最多 100 筆）"})


class FieldValuesResponse(Message):
    data = fields.List(fields.String(), metadata={"example": ["test_value_1", "test_value_2"]})


@field.route("/search", methods=["GET"])
@check_permission("product.create")
@field.arguments(FieldSearchQuery, location="query")
@field.response(200, FieldValuesResponse, description="HTTP 一律 200，錯誤看 body 的 code（400/403/404）")
@errors(field, 403)
def search_item_attribute(query):
    """搜尋某欄位已有的值（新增產品時的自動完成）"""
    results = search_item_attribute_by_field_id_and_value(query["field_id"], query.get("search_value"))
    return jsonify(results)
