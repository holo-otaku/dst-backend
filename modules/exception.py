from flask import current_app, jsonify, make_response
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(e)
            return make_response(jsonify({"code": 500, "msg": str(e)}), 500)
        except Exception as e:
            current_app.logger.error(e)
            return make_response(jsonify({"code": 500, "msg": str(e)}), 500)
        finally:
            db.session.close()
    return wrapper
