from flask_jwt_extended import get_jwt_identity, get_jwt
from models.user import User
from models.shared import db


def has_permission(required_permission):
    """檢查用戶是否有指定權限"""
    permissions = get_jwt().get("permissions", [])
    if required_permission in permissions:
        return True
    return False


def check_field_permission(permission):
    """檢查用戶對特定欄位的權限"""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    
    if user and has_permission(permission):
        return True
    return False
