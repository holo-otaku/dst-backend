from flask import current_app, jsonify, make_response, request
from models.archive import Archive
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import get_jwt_identity


def update(item_id):
    try:
        existing_archive = Archive.query.filter_by(item_id=item_id).first()

        if existing_archive:
            db.session.delete(existing_archive)
        else:
            user_id = get_jwt_identity()
            new_archive = Archive(
                item_id=item_id, archived_by=user_id)
            db.session.add(new_archive)

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
