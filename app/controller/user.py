from flask import current_app, jsonify, make_response
from models.user import User
from models.mssql import *
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


def create():
    try:
        new_user = User(name='John', age=30)
        db.session.add(new_user)
        db.session.commit()

    except SQLAlchemyError as e:
        db.session.rollback()
        print("Failed to insert data: ", e)
        return make_response(jsonify({"Code": 500, "Msg": "Failed to insert data"}), 500)

    finally:
        db.session.close()

    return make_response(jsonify({"Code": 200, "Msg": "Success"}), 200)


def read(id):
    try:
        current_app.logger.info('Read user')
        user = User.query.get(id)
        result = {}
        if user:
            result = {"name": user.name, "age": user.age}

    except SQLAlchemyError as e:
        print("Failed to read data: ", e)
        return make_response(jsonify({"Code": 500, "Msg": "No User"}), 500)

    finally:
        db.session.close()

    return make_response(jsonify({"Code": 200, "Msg": "Success", "Data": result}), 200)
