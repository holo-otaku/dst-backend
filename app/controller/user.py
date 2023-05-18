from flask import current_app, jsonify, make_response
from models.user import *
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


def create(data):
    try:
        username = data.get('username')
        password = data.get('password')
        role_id = data.get('roleId')

        if not username or not password or not role_id:
            return make_response(jsonify({"code": 200, "msg": "Incomplete data"}), 400)

        role = Role.query.get(role_id)
        if role is None:
            return make_response(jsonify({"code": 200, "msg": "Invalid role"}), 400)

        user = User(username=username, password=password)
        user.roles = [role]  # Associate user with the role

        db.session.add(user)
        db.session.commit()

        result = {'id': user.id, 'username': user.username,
                  'role': user.roles[0].name}
        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 201)

    except SQLAlchemyError as e:
        db.session.rollback()
        print("Failed to insert data: ", e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read(user_id):
    try:
        current_app.logger.info('Read user')
        user = User.query.get(user_id)

        if user is None:
            return make_response(jsonify({'code': 200, 'msg': 'User not found'}), 404)

        role_name = user.roles[0].name if user.roles else None
        result = {'id': user.id, 'userName': user.username, 'role': role_name}

        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 200)

    except SQLAlchemyError as e:
        print("Failed to read data: ", e)
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": e}), 500)

    finally:
        db.session.close()


def read_multi():
    try:
        users = User.query.all()
        result = [{'id': user.id, 'userName': user.username,
                   'role': user.roles[0].name if user.roles else None} for user in users]

        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 200)

    except SQLAlchemyError as e:
        print("Failed to read data: ", e)
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": e}), 500)

    finally:
        db.session.close()


def update(user_id, data):
    try:
        user = User.query.get(user_id)
        if user is None:
            return jsonify({'error': 'User not found'}), 404

        username = data.get('username')
        password = data.get('password')
        role_id = data.get('roleId')

        if username is not None:
            user.username = username
        if password is not None:
            user.password = password

        if role_id is not None:
            role = Role.query.get(role_id)
            if role is None:
                return make_response(jsonify({"code": 400, "msg": "Invalid role"}), 400)

            # Remove current user-role associations
            user.roles.clear()

            # Create a new user-role association
            user.roles.append(role)

        db.session.commit()

        result = {'id': user.id, 'username': user.username,
                  'role': user.roles[0].name}
        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 200)

    except SQLAlchemyError as e:
        print("Failed to update data: ", e)
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def delete(user_id):
    try:
        user = User.query.get(user_id)
        if user is None:
            return make_response(jsonify({"code": 200, "msg": 'User not found'}), 404)

        db.session.delete(user)
        db.session.commit()

        return make_response(jsonify({"code": 200, "msg": "User deleted"}), 200)

    except SQLAlchemyError as e:
        print("Failed delete data: ", e)
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": e}), 500)

    finally:
        db.session.close()
