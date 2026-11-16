"""各 router 共用的 schema。body schema 只拿來驗證和產生文件，view 仍把資料交給 controller。"""
from marshmallow import INCLUDE, Schema, fields


class Body(Schema):
    class Meta:
        # 沒列出的欄位照舊傳給 controller
        unknown = INCLUDE


class ItemIds(Body):
    itemIds = fields.List(fields.Integer(), required=True)


class Message(Schema):
    code = fields.Integer()
    msg = fields.String()


class Paging(Schema):
    page = fields.Integer(metadata={"example": 1})
    limit = fields.Integer(metadata={"example": 10})


def errors(blp, *codes):
    """文件標上 controller 會回的錯誤碼，格式都是 {"code", "msg"}。"""
    def decorator(f):
        for code in codes:
            f = blp.alt_response(code, schema=Message)(f)
        return f
    return decorator
