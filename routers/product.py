from flask_smorest import Blueprint
from marshmallow import Schema, fields

from controller.product import (
    create,
    read,
    delete,
    update_multi,
    read_multi,
    export_excel,
    create_from_items,
)
from controller.access import check_permission
from routers.schemas import Body, ItemIds, Message, Paging, errors

products = Blueprint("Products", __name__, description="產品")


VALUE = fields.Raw(
    allow_none=True,
    metadata={"description": "string | number | boolean；picture 送 data URL", "example": "17.70"},
)
FLAG = fields.Raw(metadata={"description": "0 否、1 是、2 全部（也接受 true/false）", "example": 0})


class Attribute(Body):
    fieldId = fields.Integer(required=True)
    value = VALUE


class ProductCreate(Body):
    seriesId = fields.Integer(required=True)
    attributes = fields.List(fields.Nested(Attribute))


class ProductEdit(Body):
    itemId = fields.Integer(required=True)
    attributes = fields.List(fields.Nested(Attribute))
    isDeleted = fields.Raw(metadata={"description": "0 還原、1 刪除，需要 product.delete"})


class Filter(Body):
    fieldId = fields.Integer(required=True)
    value = VALUE
    operation = fields.String(metadata={"description": "number/datetime 用：equal、greater、less"})


class Search(Body):
    seriesId = fields.Integer(required=True)
    filters = fields.List(fields.Nested(Filter))
    isDeleted = FLAG
    isArchived = FLAG


class Sort(Schema):
    sort = fields.String(metadata={"description": "fieldId,asc|desc", "example": "11,asc"})


class SearchQuery(Paging, Sort):
    pass


class DeleteIds(Body):
    itemId = fields.List(fields.Integer(), required=True)


class AttributeOut(Schema):
    fieldId = fields.Integer()
    fieldName = fields.String()
    dataType = fields.String()
    value = fields.Raw(metadata={"description": "picture 為 /image/<id>"})


class Erp(Schema):
    key = fields.String()
    value = fields.String()


class ProductOut(Schema):
    itemId = fields.Integer()
    seriesId = fields.Integer()
    seriesName = fields.String()
    attributes = fields.List(fields.Nested(AttributeOut))
    erp = fields.List(fields.Nested(Erp))
    isDeleted = fields.Boolean()
    hasArchive = fields.Boolean()


class Created(Schema):
    id = fields.Integer()
    seriesId = fields.Integer()


class CreatedResponse(Message):
    data = fields.List(fields.Nested(Created))


class ProductResponse(Message):
    data = fields.Nested(ProductOut)


class SearchResponse(Message):
    data = fields.List(fields.Nested(ProductOut))
    totalCount = fields.Integer()


# check_permission 放在最外層：沒權限先回 403，不先驗證 body
@products.route("", methods=["POST"])
@check_permission("product.create")
@products.arguments(ProductCreate(many=True))
@products.response(201, CreatedResponse)
@errors(products, 400, 403, 404)
def create_product(data):
    """新增產品（可多筆）"""
    return create(data)


@products.route("/copy", methods=["POST"])
@check_permission("product.create")
@products.arguments(ItemIds)
@products.response(201, CreatedResponse)
@errors(products, 400, 403, 404)
def copy_product(data):
    """複製產品，第一個 string 欄位加上 copy 前綴"""
    return create_from_items(data)


@products.route("/search", methods=["POST"])
@check_permission("product.read")
@products.arguments(Search)
@products.arguments(SearchQuery, location="query")
@products.response(200, SearchResponse)
@errors(products, 400, 403)
def read_multi_product(data, _query):
    """搜尋產品，合併 ERP 資料"""
    return read_multi(data)


@products.route("/export", methods=["POST"])
@check_permission("product.read")
@products.arguments(Search)
@products.arguments(Sort, location="query")
@products.response(200, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                   description="Excel 檔；沒有資料時回 {\"code\": 204}")
@errors(products, 400, 403)
def export_product(data, _query):
    """依搜尋條件匯出 Excel"""
    return export_excel(data)


@products.route("/edit", methods=["PATCH"])
@check_permission("product.edit")
@products.arguments(ProductEdit(many=True))
@products.response(200, Message)
@errors(products, 400, 403, 404)
def edit_product(data):
    """編輯產品（可多筆），也用來刪除/還原"""
    return update_multi(data)


@products.route("/delete", methods=["DELETE"])
@check_permission("product.delete")
@products.arguments(DeleteIds)
@products.response(200, Message)
@errors(products, 400, 403)
def delete_product(data):
    """軟刪除產品"""
    return delete(data)


@products.route("/<int:product_id>", methods=["GET"])
@check_permission("product.read")
@products.response(200, ProductResponse)
@errors(products, 403, 404)
def read_product(product_id):
    """取得單筆產品"""
    return read(product_id)
