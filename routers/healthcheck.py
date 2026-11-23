from flask import jsonify, make_response
from flask_smorest import Blueprint

from routers.schemas import Message

health_check = Blueprint("Health", __name__, description="連線檢查")


@health_check.route("", methods=["GET"])
@health_check.response(200, Message)
@health_check.doc(security=[])
def get():
    """連線檢查"""
    return make_response(jsonify({"code": 200, "msg": "Success"}), 200)
