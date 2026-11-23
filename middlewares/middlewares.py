from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models.shared import db
from models.log import ActivityLog
from models.user import User
from sqlalchemy import func
from middlewares.token_version import TokenVersionMiddleware
import json

# 不寫操作紀錄的路由（看第一段路徑，不用子字串比對，避免 /login 被 /log 吃掉）
SKIP_LOGGING = {"refresh", "log", "health", "image", "api", "static"}
MAX_PAYLOAD_BYTES = 100 * 1024


class Middlewares():
    def __init__(self, app) -> None:
        # 啟用 token 版本檢查 middleware
        TokenVersionMiddleware(app)

        @app.after_request
        def log_response_status(response):
            # 沒對到路由（掃描器亂打的 404）和 CORS 預檢不記
            if request.method == "OPTIONS" or request.url_rule is None:
                return response
            if request.path.strip("/").split("/")[0] in SKIP_LOGGING:
                return response
            try:
                payload = request.get_json(silent=True)
                db.session.add(ActivityLog(
                    url=request.path,
                    method=request.method,
                    user_id=_user_id(payload),
                    payload=_limit(_redact(payload)) if payload else None,
                    status=response.status_code,
                    ip=request.remote_addr,
                    user_agent=request.user_agent.string[:255] or None,
                ))
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                app.logger.error(e)
            return response


def _user_id(payload):
    # /login 記嘗試登入的帳號，密碼錯也記，才看得出有人在猜某個帳號的密碼
    if request.path == "/login":
        username = payload.get("username") if isinstance(payload, dict) else None
        if not isinstance(username, str):
            return None
        return db.session.query(User.id).filter(
            func.lower(User.username) == username.lower()).scalar()
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        return int(identity) if identity else None
    except Exception:
        # 過期、偽造的 token：仍然記一筆，只是不知道是誰
        return None


def _redact(value):
    if isinstance(value, dict):
        return {key: "***" if "password" in key.lower() else _redact(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _limit(payload):
    if len(json.dumps(payload).encode()) > MAX_PAYLOAD_BYTES:
        return {"payload": "too large"}
    return payload
