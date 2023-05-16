from flask import Blueprint
from controller.user import create, read
from flask_jwt_extended import jwt_required

user = Blueprint("user", __name__)

@user.route("/user", methods=["POST"])
# @jwt_required()
def create_user():
    return create()

@user.route("/user/<id>", methods=["GET"])
# @jwt_required()
def read_user(id):
    return read(id)