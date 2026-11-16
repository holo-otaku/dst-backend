from flask_jwt_extended import get_jwt_identity
from flask_smorest import Blueprint
# 有欄位就叫 fields，用別名避免在 class 裡蓋掉模組
from marshmallow import Schema, fields as ma

from controller.series import create, read, read_multi, update, delete
from controller.access import check_permission
from routers.schemas import Body, Message, Paging, errors

series = Blueprint("Series", __name__, description="系列（產品類型）與欄位")

DATA_TYPE = {"description": "string | number | boolean | datetime | picture", "example": "string"}


class FieldIn(Body):
    name = ma.String(required=True)
    dataType = ma.String(required=True, metadata=DATA_TYPE)
    isFiltered = ma.Boolean()
    isRequired = ma.Boolean()
    searchErp = ma.Boolean(metadata={"description": "一個系列只能有一個"})
    isErp = ma.Boolean()
    isLimitField = ma.Boolean(metadata={"description": "需要 limit-field.read 才看得到"})
    sequence = ma.Integer(allow_none=True)


class FieldEdit(FieldIn):
    name = ma.String()
    id = ma.Integer(allow_none=True, metadata={"description": "沒有 id 的會被略過，新欄位放 create"})


class SeriesCreate(Body):
    name = ma.String(required=True)
    fields = ma.List(ma.Nested(FieldIn), metadata={"description": "必須包含「供應商料號」和「DST料號」"})


class SeriesUpdate(Body):
    name = ma.String()
    fields = ma.List(ma.Nested(FieldEdit))
    create = ma.List(ma.Nested(FieldIn))
    delete = ma.List(ma.Integer(), metadata={"description": "要刪除的欄位 id，必填欄位不能刪"})


class SeriesQuery(Paging):
    keyword = ma.String()
    showField = ma.Integer(metadata={"description": "1 時附上欄位", "example": 0})


class FieldOut(Schema):
    id = ma.Integer(allow_none=True, metadata={"description": "還沒存的 ERP 欄位為 null"})
    name = ma.String()
    dataType = ma.String(metadata=DATA_TYPE)
    isFiltered = ma.Boolean()
    isRequired = ma.Boolean()
    searchErp = ma.Boolean()
    isErp = ma.Boolean()
    isLimitField = ma.Boolean()
    sequence = ma.Integer()


class SeriesOut(Schema):
    id = ma.Integer()
    name = ma.String()
    createdBy = ma.String()
    createdAt = ma.String(metadata={"example": "2025-01-01 12:00:00"})
    fields = ma.List(ma.Nested(FieldOut))


class SeriesResponse(Message):
    data = ma.Nested(SeriesOut)


class SeriesListResponse(Message):
    data = ma.List(ma.Nested(SeriesOut))
    totalCount = ma.Integer()


class SeriesCreated(Schema):
    id = ma.Integer()
    name = ma.String()
    createdBy = ma.Integer()


class SeriesCreatedResponse(Message):
    data = ma.Nested(SeriesCreated)


# check_permission 放在最外層：沒權限先回 403，不先驗證 body
@series.route("", methods=["GET"])
@check_permission('series.read')
@series.arguments(SeriesQuery, location="query")
@series.response(200, SeriesListResponse)
@errors(series, 403)
def get_serieses(_query):
    """系列列表"""
    return read_multi()


@series.route("/<int:series_id>", methods=["GET"])
@check_permission('series.read')
@series.response(200, SeriesResponse)
@errors(series, 403, 404)
def get_series(series_id):
    """取得系列與欄位，有 searchErp 欄位時附上 ERP 欄位"""
    return read(series_id)


@series.route("", methods=["POST"])
@check_permission('series.create')
@series.arguments(SeriesCreate)
@series.response(201, SeriesCreatedResponse)
@errors(series, 400, 403)
def create_series(data):
    """新增系列"""
    return create(data, int(get_jwt_identity()))


@series.route("<int:series_id>", methods=["PATCH"])
@check_permission('series.edit')
@series.arguments(SeriesUpdate)
@series.response(200, Message)
@errors(series, 400, 403, 404)
def update_series(data, series_id):
    """編輯系列：fields 改既有欄位、create 新增、delete 刪除"""
    return update(series_id, data)


@series.route("<int:series_id>", methods=["DELETE"])
@check_permission('series.delete')
@series.response(200, Message)
@errors(series, 403, 404)
def delete_series(series_id):
    """刪除系列（軟刪除）"""
    return delete(series_id)
