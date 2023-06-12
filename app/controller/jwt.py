from flask import current_app, request, jsonify, make_response
from flask_jwt_extended import (create_access_token, get_jwt_identity)
from datetime import timedelta
from models.user import User
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


def login():
    try:
        username = request.json.get("username", None)
        password = request.json.get("password", None)

        # 在用户数据库中查找匹配的用户
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            # 如果找到匹配的用户且密碼相符，就发出一个 JWT token
            access_token = create_access_token(identity=user.id)
            return make_response(jsonify({"code": 200, "msg": "login success", "data": {"access_token": access_token}}), 200)
        else:
            return make_response(jsonify({"msg": "Invalid credentials"}), 401)

    except SQLAlchemyError as e:
        db.session.rollback()
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def refresh():
    try:
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
        return make_response(jsonify({"accessToken": new_token}), 200)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)
