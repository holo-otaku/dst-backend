from flask import current_app, jsonify, make_response, request
from models.user import User, Role
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


def create_admin_user():
    try:
        if not User.query.first():
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(username='admin')
                admin_user.set_password('admin')
                admin_role = Role.query.filter_by(name='admin').first()
                admin_user.roles.append(admin_role)
                db.session.add(admin_user)
                current_app.logger.info("Default admin account created.")
            else:
                current_app.logger.info("Default admin account exist.")

            db.session.commit()
        else:
            current_app.logger.info("Default admin account exist.")

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)

    except Exception as e:
        current_app.logger.error(e)

    finally:
        db.session.close()


def create(data):
    try:
        username = data.get('username')
        password = data.get('password')
        role_id = data.get('roleId')

        if not username or not password or not role_id:
            return make_response(jsonify({"code": 200, "msg": "Incomplete data"}), 400)

        role = db.session.get(Role, role_id)

        if role is None:
            return make_response(jsonify({"code": 200, "msg": "Invalid role"}), 400)

        user = User(username=username)
        user.set_password(password)
        user.roles = [role]  # Associate user with the role

        db.session.add(user)
        db.session.commit()

        result = {'id': user.id, 'username': user.username,
                  'role': user.roles[0].name}
        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 201)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read(user_id):
    try:
        user = db.session.get(User, user_id)

        if user is None:
            return make_response(jsonify({'code': 200, 'msg': 'User not found'}), 404)

        role_name = user.roles[0].name if user.roles else None
        role_id = user.roles[0].id if user.roles else None
        result = {'userName': user.username,
                  'role': role_name, 'roleId': role_id}

        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 200)

    except SQLAlchemyError as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": e}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read_multi():
    try:
        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        users = User.query.limit(limit).offset((page - 1) * limit).all()
        result = [{'id': user.id, 'userName': user.username,
                   'role': user.roles[0].name if user.roles else None} for user in users]

        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 200)

    except SQLAlchemyError as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": e}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def update(user_id, data):
    try:
        user = db.session.get(User, user_id)
        if user is None:
            return jsonify({'error': 'User not found'}), 404

        username = data.get('username')
        password = data.get('password')
        role_id = data.get('roleId')

        if username is not None:
            user.username = username
        if password is not None:
            user.set_password(password)

        if role_id is not None:
            role = db.session.get(Role, role_id)

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
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def delete(user_id):
    try:
        user = db.session.get(User, user_id)
        if user is None:
            return make_response(jsonify({"code": 200, "msg": 'User not found'}), 404)

        db.session.delete(user)
        db.session.commit()

        return make_response(jsonify({"code": 200, "msg": "User deleted"}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": e}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()
