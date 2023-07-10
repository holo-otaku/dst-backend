from flask import Blueprint, jsonify, make_response

health_check = Blueprint("health", __name__)


@health_check.route("", methods=["GET"])
def get():

    return make_response(jsonify({"code": 200, "msg": "Success"}), 200)
