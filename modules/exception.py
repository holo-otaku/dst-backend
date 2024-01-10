from flask import current_app, jsonify, make_response
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError
import traceback


def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except SQLAlchemyError as e:
            db.session.rollback()
            error_message = str(e)
            traceback_str = traceback.format_exc()
            current_app.logger.error(traceback_str)
            return make_response(jsonify({"code": 500, "msg": error_message}), 500)
        except Exception as e:
            error_message = str(e)
            traceback_str = traceback.format_exc()
            current_app.logger.error(traceback_str)
            return make_response(jsonify({"code": 500, "msg": error_message}), 500)
        finally:
            db.session.close()
    return wrapper
