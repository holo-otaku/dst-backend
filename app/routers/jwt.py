from flask import Blueprint
from flask_jwt_extended import (
    jwt_required, create_access_token, get_jwt_identity)
from flask import jsonify
from datetime import timedelta
from controller.jwt import login


jwt = Blueprint("jwt", __name__)


@jwt.route("/jwt/refresh", methods=["POST"])
@jwt_required
def refresh():
    # 獲取當前用戶的 ID
    current_user = get_jwt_identity()
    # 獲取當前用戶的 JWT Token 的加密內容
    # jwt_token = get_raw_jwt()

    # 檢查 JWT Token 是否在黑名單中，如果是，則無法進行刷新
    # if jwt_token in blacklist:
    #     return jsonify({"msg": "Invalid token"}), 401

    # 創建新的 JWT Token，有效期為 30 分鐘
    new_token = create_access_token(
        identity=current_user, expires_delta=timedelta(minutes=30))

    # 返回新的 JWT Token 給用戶
    return jsonify({"access_token": new_token}), 200


@jwt.route("/login", methods=["POST"])
def user_login():
    login()
