from flask import current_app, request, jsonify, make_response
from flask_jwt_extended import (create_access_token, get_jwt_identity)
from datetime import timedelta
from models.user import User
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


def login():
    try:
        if not request.json:
            return make_response(jsonify({"msg": "Invalid request"}), 400)

        username = request.json.get("username", None)
        password = request.json.get("password", None)

        # 在用户数据库中查找匹配的用户
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            access_token = __create_access_token(user)
            return make_response(jsonify({"code": 200, "msg": "login success", "data": {"accessToken": access_token}}), 200)
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
        user = db.session.query(User).filter_by(id=current_user).first()

        if not user:
            return make_response(jsonify({"code": 404, "msg": "User not found"}), 404)

        # 創建新的 JWT Token，有效期為 30 分鐘
        new_token = __create_access_token(user)

        # 返回新的 JWT Token 給用戶
        return make_response(jsonify({"accessToken": new_token}), 200)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)


def __create_access_token(user):
    permissions = []
    for role in user.roles:
        for permission in role.permissions:
            permissions.append(permission.name)

    return create_access_token(identity=user.id,
                               additional_claims={"userName": user.username, "permissions": permissions})
