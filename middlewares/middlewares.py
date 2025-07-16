from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_jwt_extended.exceptions import NoAuthorizationError
from models.shared import db
from models.log import ActivityLog
from middlewares.token_version import TokenVersionMiddleware
import json
import zlib
import sys


class Middlewares():
    def __init__(self, app) -> None:
        # 啟用 token 版本檢查 middleware
        TokenVersionMiddleware(app)
        
        @app.after_request
        def log_response_status(response):
            try:
                # Skip logging for login and refresh endpoints
                skip_logging_endpoints = [
                    "login", "refresh", "log", "health", "image"]
                if any(endpoint in request.path for endpoint in skip_logging_endpoints):
                    return response

                # Check if JWT is required for this request
                if not any(endpoint in request.path for endpoint in ["no_jwt_required"]):
                    verify_jwt_in_request()  # Only verify JWT if required

                # Attempt to get user identity
                user_id = get_jwt_identity() if verify_jwt_in_request() else None

                log_data = {
                    'url': request.path,
                    'user_id': user_id
                }

                # If endpoint contains 'user', skip logging payload
                if "user" in request.path or "image" in request.path:
                    return response

                # Log URL, user ID, and payload (if available)
                payload = request.get_json(silent=True)

                if payload:
                    log_data['payload'] = payload

                # Store log_data in your database
                activity_log = ActivityLog(
                    url=log_data['url'],
                    method=request.method,
                    user_id=log_data['user_id'])

                if log_data.get('payload'):
                    activity_log.payload = self.__compress_json(
                        log_data['payload'])

                db.session.add(activity_log)
                db.session.commit()

                return response
            except Exception as e:
                app.logger.error(e)
                return response

    def __compress_json(self, payload):  # 将方法定义为实例方法，并添加 self 参数
        json_str = json.dumps(payload)
        size_in_bytes = sys.getsizeof(json_str)
        if size_in_bytes > 100 * 1024:  # 超过100KB
            return {"payload": "too large"}
        return payload
