from flask import Blueprint
from controller.user import create, read

user = Blueprint("user", __name__)

user.route("/user", methods=["POST"])(create)
user.route("/user/<id>", methods=["GET"])(read)
