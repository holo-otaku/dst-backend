from flask import current_app, jsonify, make_response
from models.shared import db
import traceback


def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception:
            db.session.rollback()
            current_app.logger.error(traceback.format_exc())
            # 細節只寫 log，不回給前端（可能含 SQL、路徑）
            return make_response(jsonify({"code": 500, "msg": "Internal server error"}), 500)
        finally:
            db.session.close()
    return wrapper
