from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields

from controller.jwt import login, refresh
from routers.schemas import Body, Message, errors

jwt = Blueprint("Login", __name__, description="登入與換發 token")


class LoginBody(Body):
    # 只產生文件不驗證：格式錯也要和帳密錯一樣回 401，由 controller 判斷
    username = fields.Raw(metadata={"type": "string", "description": "必填", "example": "admin"})
    password = fields.Raw(metadata={"type": "string", "description": "必填", "example": "admin"})


class Token(Schema):
    accessToken = fields.String()


class LoginResponse(Message):
    data = fields.Nested(Token)


@jwt.route("/jwt/refresh", methods=["POST"])
@jwt_required()
@jwt.response(200, Token)
@errors(jwt, 401, 403, 404)
def user_refresh():
    """換發 access token（token 已撤銷時回 401 + forceLogout）"""
    return refresh()


@jwt.route("/login", methods=["POST"])
@jwt.arguments(LoginBody)
@jwt.response(200, LoginResponse)
@errors(jwt, 401, 403)
@jwt.doc(security=[])
def user_login(_data):
    """登入，回傳 access token"""
    return login()
