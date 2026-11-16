import json

import flask_smorest
from flask_smorest.error_handler import ErrorSchema
from marshmallow import fields


class Error(ErrorSchema):
    msg = fields.String(metadata={"description": "錯誤訊息，驗證錯誤時為 errors 的 JSON"})


class Api(flask_smorest.Api):
    ERROR_SCHEMA = Error

    def handle_http_exception(self, error):
        payload, code, headers = super().handle_http_exception(error)
        # 前端顯示 msg，格式和 controller 回的 {"code", "msg"} 一致
        errors = payload.get("errors")
        payload["msg"] = json.dumps(errors, ensure_ascii=False) if errors else error.description
        return payload, code, headers


def create_api(app):
    """API 文件由 flask_smorest.Blueprint 的 schema 產生，ENABLE_SWAGGER 時才開放 /api/docs/。"""
    if app.config.get("ENABLE_SWAGGER"):
        app.config.update(
            OPENAPI_URL_PREFIX="/api/docs",
            OPENAPI_SWAGGER_UI_PATH="/",
            OPENAPI_SWAGGER_UI_URL="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/",
        )
    api = Api(app, spec_kwargs={
        "title": "DST API",
        "version": "1.0.0",
        "openapi_version": "3.0.3",
        # 預設要登入；公開的 API 用 @blp.doc(security=[]) 覆寫
        "security": [{"bearerAuth": []}],
    })
    api.spec.components.security_scheme(
        "bearerAuth", {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"})
    return api
