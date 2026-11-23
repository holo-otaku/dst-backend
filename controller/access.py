from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from flask import current_app, jsonify, make_response
from functools import wraps
from models.user import User
from models.shared import db


def check_permission(permission):
    def decorator(f):
        @wraps(f)
        @jwt_required(optional=True)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()

            if not user_id:
                return make_response(jsonify({"code": 403, "msg": "Permission denied"}), 403)

            user = db.session.get(User, int(user_id))

            if user and has_permission(user, permission):
                # 有權限，執行原始函數
                return f(*args, **kwargs)
            else:
                # has_permission 已經寫過 warning；完整紀錄在 activity_log / audit.log（status 403）
                return make_response(jsonify({"code": 403, "msg": "Permission denied"}), 403)

        return wrapper
    return decorator


def can_grant(permission_names):
    """A caller may only grant permissions it already holds."""
    return set(permission_names) <= set(get_jwt().get("permissions", []))


def has_permission(user, required_permission):
    permissions = get_jwt().get("permissions", [])
    if required_permission in permissions:
        return True
    current_app.logger.warning(
        f"{user.username} try to access {required_permission}")
    return False
