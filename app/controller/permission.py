from flask import current_app, jsonify, make_response
from models.user import *
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


def create(data):
    try:
        name = data.get('name')

        if not name:
            return make_response(jsonify({"code": 200, "msg": 'Incomplete data'}), 400)

        existing_permission = Permission.query.filter_by(name=name).first()
        if existing_permission:
            return make_response(jsonify({"code": 200, "msg": 'Permission name already exists'}), 400)

        permission = Permission(name=name)
        db.session.add(permission)
        db.session.commit()
        return make_response(jsonify({"code": 200, "msg": "Permission created"}), 200)

    except SQLAlchemyError as e:
        print("Failed to create permission: ", e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)


def read(permission_id):
    try:
        permission = Permission.query.get(permission_id)
        if permission is None:
            return make_response(jsonify({"code": 404, "msg": 'Permission not found'}), 404)

        result = {'id': permission.id, 'name': permission.name}

        return make_response(jsonify({"code": 200, "msg": "Permission found", "data": result}), 200)

    except SQLAlchemyError as e:
        print("Failed to get permission: ", e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)


def read_multi():
    try:
        permissions = Permission.query.all()

        result = [{'id': permission.id, 'name': permission.name} for permission in permissions]

        return make_response(jsonify({"code": 200, "msg": "Permission found", "data": result}), 200)

    except SQLAlchemyError as e:
        print("Failed to get permission: ", e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)


def update(permission_id, data):
    try:
        permission = Permission.query.get(permission_id)
        if permission is None:
            return make_response(jsonify({"code": 404, "msg": 'Permission not found'}), 404)

        name = data.get('name')
        if name:
            permission.name = name

        db.session.commit()

        return make_response(jsonify({"code": 200, "msg": "Permission updated"}), 200)

    except SQLAlchemyError as e:
        print("Failed to update permission: ", e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)


def delete(permission_id):
    try:
        permission = Permission.query.get(permission_id)
        if permission is None:
            return make_response(jsonify({"code": 404, "msg": 'Permission not found'}), 404)

        db.session.delete(permission)
        db.session.commit()

        return make_response(jsonify({"code": 200, "msg": "Permission deleted"}), 200)

    except SQLAlchemyError as e:
        print("Failed to delete permission: ", e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)
