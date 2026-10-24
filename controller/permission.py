from flask import current_app, jsonify, make_response, request
from models.user import Permission
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError
from models.mapping_table import permissions_table
from modules.exception import handle_exceptions
from controller.access import can_grant


def __revoke_holders(permission):
    """讓擁有此權限的使用者重新登入，舊 token 的權限才會失效"""
    for role in permission.roles:
        for user in role.users:
            user.token_version += 1


@handle_exceptions
def create_default_permissions():
    permissions = permissions_table

    for permission in permissions:
        existing_permission = Permission.query.filter_by(
            name=permission).first()
        if not existing_permission:
            new_permission = Permission(name=permission)
            db.session.add(new_permission)
    db.session.commit()


@handle_exceptions
def create(data):
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


@handle_exceptions
def read(permission_id):
    permission = db.session.get(Permission, permission_id)

    if permission is None:
        return make_response(jsonify({"code": 404, "msg": 'Permission not found'}), 404)

    result = {'id': permission.id, 'name': permission.name}

    return make_response(jsonify({"code": 200, "msg": "Permission found", "data": result}), 200)


@handle_exceptions
def read_multi():
    # Pagination parameters
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))

    permissions = Permission.query.limit(
        limit).offset((page - 1) * limit).all()

    total_count = Permission.query.count()

    result = [{'id': permission.id, 'name': permission.name}
              for permission in permissions]

    return make_response(jsonify({"code": 200, "msg": "Permission found", "data": result, "totalCount": total_count}), 200)


@handle_exceptions
def update(permission_id, data):
    permission = db.session.get(Permission, permission_id)

    if permission is None:
        return make_response(jsonify({"code": 404, "msg": 'Permission not found'}), 404)

    name = data.get('name')
    if name and name != permission.name:
        # 改名等於改變權限的意義，只有持有全部權限的人可以做
        if not can_grant(p.name for p in Permission.query.all()):
            return make_response(jsonify({"code": 403, "msg": "Permission denied"}), 403)
        __revoke_holders(permission)
        permission.name = name

    db.session.commit()

    return make_response(jsonify({"code": 200, "msg": "Permission updated"}), 200)


@handle_exceptions
def delete(permission_id):
    permission = db.session.get(Permission, permission_id)

    if permission is None:
        return make_response(jsonify({"code": 404, "msg": 'Permission not found'}), 404)

    __revoke_holders(permission)
    db.session.delete(permission)
    db.session.commit()

    return make_response(jsonify({"code": 200, "msg": "Permission deleted"}), 200)
