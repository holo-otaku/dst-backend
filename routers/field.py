from flask import Blueprint, request, jsonify
from controller.field import search_item_attribute_by_field_id_and_value
from controller.access import check_permission

field = Blueprint("field", __name__)

@field.route("/search", methods=["GET"])
@check_permission("product.create")
def search_item_attribute():
    """
    @api {get} /field/search 搜尋 ItemAttribute
    @apiName SearchItemAttribute
    @apiGroup Field
    @apiParam {Number} field_id 欄位 ID
    @apiParam {String} search_value 搜尋值
    @apiSuccess {Number} code 狀態碼 (200: 成功, 400: 參數錯誤, 500: 伺服器錯誤)
    @apiSuccess {String} msg 訊息
    @apiSuccess {Object[]} data 搜尋結果列表
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
            "code": 200,
            "msg": "Success",
            "data": [
                "test_value_1",
                "test_value_2"
            ]
        }
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 400 Bad Request
        {
            "code": 400,
            "msg": "Missing field_id or search_value",
            "data": []
        }
    """
    field_id = request.args.get("field_id", type=int)
    search_value = request.args.get("search_value", type=str)

    results = search_item_attribute_by_field_id_and_value(field_id, search_value)
    return jsonify(results)
