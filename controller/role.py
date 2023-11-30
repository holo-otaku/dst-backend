from flask import current_app, jsonify, make_response, request
from models.user import Permission, Role, RolePermission
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


def create_admin_role():
    try:
        admin_role = Role.query.filter_by(name='admin').first()

        permissions = Permission.query.all()

        if admin_role:
            existing_permissions = set(
                permission.name for permission in admin_role.permissions)
            for permission in permissions:
                if permission.name not in existing_permissions:
                    admin_role.permissions.append(permission)
        else:
            admin_role = Role(name='admin')
            admin_role.permissions.extend(permissions)
            db.session.add(admin_role)

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
        role_name = data.get('roleName')
        permission_ids = data.get('permissionIds')

        # 檢查 roleName 是否重複
        existing_role = Role.query.filter_by(name=role_name).first()
        if existing_role:
            return make_response(jsonify({"code": 400, "msg": f"Role with name '{role_name}' already exists"}), 400)

        # 檢查 permission_ids 是否存在
        for permission_id in permission_ids:
            permission = Permission.query.get(permission_id)

            if not permission:
                return make_response(jsonify({"code": 400, "msg": f"Permission with ID {permission_id} not found"}), 400)

        role = Role(name=role_name)
        db.session.add(role)
        db.session.commit()

        __update_role_permissions(role.id, permission_ids)

        return make_response(jsonify({"code": 200, "msg": "Role created", "data": {"id": role.id}}), 201)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def update(role_id, data):
    try:
        # 查询要更新的角色
        role = Role.query.get(role_id)

        if role is None:
            return make_response(jsonify({"code": 200, "msg": 'Role not found'}), 404)

        role.name = data.get('roleName')
        db.session.commit()

        permission_ids = data.get('permissionIds')
        __update_role_permissions(role.id, permission_ids)

        return make_response(jsonify({"code": 200, "msg": "Role updated"}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def __update_role_permissions(role_id, permission_ids):
    # 先移除角色原有的权限关联
    RolePermission.query.filter_by(role_id=role_id).delete()

    # 创建新的角色权限关联
    for permission_id in permission_ids:
        role_permission = RolePermission(
            role_id=role_id, permission_id=permission_id)
        db.session.add(role_permission)

    db.session.commit()


def delete(role_id):
    try:
        role = Role.query.get(role_id)

        if role is None:
            return make_response(jsonify({"code": 200, "msg": 'Role not found'}), 404)

        # 删除角色权限关联
        RolePermission.query.filter_by(role_id=role_id).delete()

        db.session.delete(role)
        db.session.commit()

        return make_response(jsonify({"code": 200, "msg": "Role deleted"}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read(role_id):
    try:
        role = Role.query.get(role_id)

        if role is None:
            return make_response(jsonify({"code": 404, "msg": 'Role not found'}), 404)

        permissions = [{'id': permission.id, 'name': permission.name}
                       for permission in role.permissions]

        result = {'id': role.id, 'name': role.name, 'permissions': permissions}

        return make_response(jsonify({"code": 200, "msg": "Role found", "data": result}), 200)

    except SQLAlchemyError as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

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

        roles = Role.query.limit(limit).offset((page - 1) * limit).all()

        total_count = Role.query.count()

        result = [{'id': role.id, 'name': role.name, 'permissions': [
            {'id': permission.id, 'name': permission.name} for permission in role.permissions]} for role in roles]

        return make_response(jsonify({"code": 200, "msg": "Roles found", "data": result, "totalCount": total_count}), 200)

    except SQLAlchemyError as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()
