from flask import current_app, jsonify, make_response, request
from models.user import Permission
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError
from models.mapping_table import permissions_table


def create_default_permissions():
    try:
        permissions = permissions_table

        for permission in permissions:
            existing_permission = Permission.query.filter_by(
                name=permission).first()
            if not existing_permission:
                new_permission = Permission(name=permission)
                db.session.add(new_permission)
        db.session.commit()

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)

    except Exception as e:
        current_app.logger.error(e)

    finally:
        db.session.close()


def create(data):
    try:
        name = data.get('name')

        if not name:
            return make_response(jsonify({"code": 400, "msg": 'Incomplete data'}), 400)

        existing_permission = Permission.query.filter_by(name=name).first()
        if existing_permission:
            return make_response(jsonify({"code": 400, "msg": 'Permission name already exists'}), 400)

        permission = Permission(name=name)
        db.session.add(permission)
        db.session.commit()

        permission_data = {
            'id': permission.id,
            'name': permission.name
        }
        return make_response(jsonify({"code": 200, "msg": "Permission created", "data": permission_data}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read(permission_id):
    try:
        permission = Permission.query.get(permission_id)

        if permission is None:
            return make_response(jsonify({"code": 404, "msg": 'Permission not found'}), 404)

        result = {'id': permission.id, 'name': permission.name}

        return make_response(jsonify({"code": 200, "msg": "Permission found", "data": result}), 200)

    except SQLAlchemyError as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)


def read_multi():
    try:
        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        permissions = Permission.query.limit(
            limit).offset((page - 1) * limit).all()

        total_count = Permission.query.count()

        result = [{'id': permission.id, 'name': permission.name}
                  for permission in permissions]

        return make_response(jsonify({"code": 200, "msg": "Permission found", "data": result, "totalCount": total_count}), 200)

    except SQLAlchemyError as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
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
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def delete(permission_id):
    try:
        permission = Permission.query.get(permission_id)

        if permission is None:
            return make_response(jsonify({"code": 404, "msg": 'Permission not found'}), 404)

        db.session.delete(permission)
        db.session.commit()

        return make_response(jsonify({"code": 200, "msg": "Permission deleted"}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()
