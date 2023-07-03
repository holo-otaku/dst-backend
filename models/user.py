from models.shared import db
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)

    roles = relationship('Role', secondary='user_role', backref='users')


class UserRole(db.Model):
    __tablename__ = 'user_role'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)


class Role(db.Model):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    permissions = relationship('Permission', secondary='role_permission', backref='roles')

class Permission(db.Model):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)


class RolePermission(db.Model):
    __tablename__ = 'role_permission'
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    permission_id = Column(Integer, ForeignKey(
        'permissions.id'), primary_key=True)
