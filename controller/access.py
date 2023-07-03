from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import current_app, jsonify, make_response
from functools import wraps
from models.user import User, Permission, Role, RolePermission, UserRole
from models.shared import db


def check_permission(permission):
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)

            if has_permission(user, permission):
                # 有權限，執行原始函數
                return f(*args, **kwargs)
            else:
                # 沒有權限，回傳拒絕訪問的訊息
                return make_response(jsonify({"code": 403, "msg": "Permission denied"}), 403)

        return wrapper
    return decorator


def has_permission(user, required_permission):
    permissions = db.session.query(Permission).join(RolePermission).join(
        Role).join(UserRole).filter(UserRole.user_id == user.id).all()
    for permission in permissions:
        if permission.name == required_permission:
            return True

    return False
