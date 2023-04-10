from flask import render_template, current_app
from models.user import User
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


def create():
    try:
        new_user = User(name='John', age=30)
        db.session.add(new_user)
        db.session.commit()

        return {"Code": 200, "Msg": "Success"}
    except SQLAlchemyError as e:
        db.session.rollback()
        print("Failed to insert data: ", e)
    finally:
        db.session.close()


def read(id):
    try:
        current_app.logger.info('Read user')
        user = User.query.get(id)
        result = {}
        if user:
            result = {"name": user.name, "age": user.age}

        return {"Code": 200, "Msg": "Success", "Data": result}
    except SQLAlchemyError as e:
        print("Failed to read data: ", e)
    finally:
        db.session.close()
