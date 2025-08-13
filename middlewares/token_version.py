from flask import request, jsonify, make_response
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from flask_jwt_extended.exceptions import NoAuthorizationError, JWTExtendedException
from models.shared import db
from models.user import User


class TokenVersionMiddleware:
    def __init__(self, app):
        @app.before_request
        def check_token_version():
            # 跳過不需要 JWT 的路由
            skip_endpoints = [
                '/login', '/refresh', '/health', '/swagger', '/static'
            ]
            
            if any(endpoint in request.path for endpoint in skip_endpoints):
                return
                
            # 跳過 OPTIONS 請求
            if request.method == 'OPTIONS':
                return
                
            try:
                # 驗證 JWT 是否存在
                verify_jwt_in_request()
                
                # 獲取使用者 ID 和 JWT claims
                user_id = get_jwt_identity()
                claims = get_jwt()
                
                # 檢查 token 中的版本號
                token_version = claims.get('tokenVersion', 0)
                
                # 從資料庫獲取使用者資訊
                user = db.session.query(User).filter_by(id=user_id).first()
                
                if not user:
                    return make_response(jsonify({
                        "code": 401,
                        "msg": "User not found"
                    }), 401)
                
                # 檢查使用者是否被停用
                if user.is_disabled:
                    return make_response(jsonify({
                        "code": 403,
                        "msg": "User account is disabled",
                        "forceLogout": True
                    }), 403)
                
                # 檢查 token 版本是否匹配
                if user.token_version != token_version:
                    return make_response(jsonify({
                        "code": 401,
                        "msg": "Token has been revoked. Please login again.",
                        "forceLogout": True
                    }), 401)
                    
            except NoAuthorizationError:
                # 沒有 JWT token
                return make_response(jsonify({
                    "code": 401,
                    "msg": "Missing Authorization Header"
                }), 401)
                
            except JWTExtendedException as e:
                # JWT 相關錯誤
                return make_response(jsonify({
                    "code": 401,
                    "msg": str(e)
                }), 401)
                
            except Exception as e:
                # 其他錯誤
                return make_response(jsonify({
                    "code": 500,
                    "msg": "Internal server error"
                }), 500)
