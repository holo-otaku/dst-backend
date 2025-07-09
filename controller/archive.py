from flask import current_app, jsonify, make_response, request
from models.archive import Archive
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import get_jwt_identity
from modules.exception import handle_exceptions


@handle_exceptions
def create(data):
    item_ids = data.get("itemIds", [])  # 多筆封存 item_id 的 list
    user_id = get_jwt_identity()

    if not item_ids:
        return make_response(jsonify({"code": 400, "msg": "No itemIds provided"}), 400)

    created_count = 0
    skipped_ids = []

    for item_id in item_ids:
        existing = Archive.query.filter_by(item_id=item_id, archived_by=user_id).first()
        if existing:
            skipped_ids.append(item_id)
            continue

        new_archive = Archive(item_id=item_id, archived_by=user_id)
        db.session.add(new_archive)
        created_count += 1

    db.session.commit()

    return make_response(
        jsonify(
            {
                "code": 200,
                "msg": f"Archived {created_count} items, skipped {len(skipped_ids)} duplicates",
                "data": {
                    "skipped": skipped_ids,
                },
            }
        ),
        200,
    )


@handle_exceptions
def delete(data):
    item_ids = data.get("itemIds", [])

    if not item_ids:
        return make_response(jsonify({"code": 400, "msg": "No itemIds provided"}), 400)

    deleted_ids = []
    not_found_ids = []

    for item_id in item_ids:
        archive = Archive.query.filter_by(item_id=item_id).first()
        if archive:
            db.session.delete(archive)
            deleted_ids.append(item_id)
        else:
            not_found_ids.append(item_id)

    db.session.commit()

    return make_response(
        jsonify(
            {
                "code": 200,
                "msg": f"Deleted {len(deleted_ids)} items, {len(not_found_ids)} not found",
                "data": {
                    "deleted": deleted_ids,
                    "notFound": not_found_ids,
                },
            }
        ),
        200,
    )
