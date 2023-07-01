from flask import Blueprint
from flask_jwt_extended import jwt_required
from controller.jwt import login, refresh


jwt = Blueprint("jwt", __name__)


@jwt.route("/jwt/refresh", methods=["POST"])
@jwt_required()
def user_refresh():
    return refresh()


@jwt.route("/login", methods=["POST"])
def user_login():
    return login()
