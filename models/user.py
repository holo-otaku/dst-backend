from models.shared import db
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(256), nullable=False)  # 增加密碼欄位長度
    token_version = Column(Integer, nullable=False, default=1)  # 用於強制登出的版本控制

    roles = relationship('Role', secondary='user_role', backref='users')
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)  # 將密碼加密

    def check_password(self, password):
        return check_password_hash(self.password, password)  # 檢查密碼是否相符Ｆ


class UserRole(db.Model):
    __tablename__ = 'user_role'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)


class Role(db.Model):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)

    permissions = relationship(
        'Permission', secondary='role_permission', backref='roles')


class Permission(db.Model):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)


class RolePermission(db.Model):
    __tablename__ = 'role_permission'
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    permission_id = Column(Integer, ForeignKey(
        'permissions.id'), primary_key=True)
