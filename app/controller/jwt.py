from flask import current_app, request, jsonify
from flask_jwt_extended import create_access_token
from models.user import User
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


def login():
    try:
        username = request.json.get("username", None)
        password = request.json.get("password", None)

        # 在用户数据库中查找匹配的用户
        user = next(
            (u for u in users if u["username"] == username and u["password"] == password), None)

        if user:
            # 如果找到匹配的用户，就发出一个 JWT token
            access_token = create_access_token(identity=user["id"])
            return jsonify({"access_token": access_token}), 200
        else:
            return jsonify({"Msg": "Invalid credentials"}), 401

    except SQLAlchemyError as e:
        db.session.rollback()
        print("Failed to insert data: ", e)
    finally:
        db.session.close()
