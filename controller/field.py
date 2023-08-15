from flask import current_app, jsonify, make_response, request
from models.shared import db
from models.series import Field
from sqlalchemy.exc import SQLAlchemyError


def update(field_id, data):
    try:
        field = db.session.get(Field, field_id)

        if not field:
            return make_response(jsonify({"code": 404, "msg": "Field not found"}), 404)

        is_filtered = data.get("isFiltered", None)
        is_required = data.get("isRequired", None)
        is_erp = data.get("isErp", None)

        if is_filtered is not None:
            field.is_filtered = bool(int(is_filtered))
        if is_required is not None:
            field.is_required = bool(int(is_required))
        if is_erp is not None:
            field.is_erp = bool(int(is_erp))

        db.session.commit()

        return make_response(jsonify({"code": 200, "msg": "Success"}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()
