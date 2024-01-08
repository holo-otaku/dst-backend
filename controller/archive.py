from flask import current_app, jsonify, make_response, request
from models.archive import Archive
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import get_jwt_identity
from modules.exception import handle_exceptions


@handle_exceptions
def create(data):
    item_id = data.get('itemId')
    user_id = get_jwt_identity()

    existing_archive = Archive.query.filter_by(
        item_id=item_id, archived_by=user_id).first()

    if existing_archive:
        return make_response(jsonify({"code": 200, "msg": "Archive already exists"}), 200)

    new_archive = Archive(item_id=item_id, archived_by=user_id)
    db.session.add(new_archive)
    db.session.commit()

    return make_response(jsonify({"code": 200, "msg": "Success"}), 200)


@handle_exceptions
def delete(item_id):
    existing_archive = Archive.query.filter_by(item_id=item_id).first()

    if not existing_archive:
        return make_response(jsonify({"code": 400, "msg": "Item not exist"}), 400)

    db.session.delete(existing_archive)

    db.session.commit()

    return make_response(jsonify({"code": 200, "msg": "Success"}), 200)
