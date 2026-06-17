"""Regression tests for JWT identity handling.

PyJWT >= 2.12 (pulled in by the security upgrade) requires the `sub` claim to
be a string and raises "Subject must be a string" otherwise. Tokens must
therefore be created with a string identity, while the application code keeps
treating the user id as an int. These tests exercise the REAL encode/decode
path (no mocking of PyJWT) so this breakage cannot regress silently.
"""
from unittest.mock import MagicMock

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, decode_token

from controller.jwt import __create_access_token as create_access_token_for_user


@pytest.fixture
def jwt_app():
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests-only"
    JWTManager(app)
    return app


def _fake_user(user_id=7, username="alice", token_version=3, perms=("series.create",)):
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.token_version = token_version
    role = MagicMock()
    role.permissions = [MagicMock(name=p) for p in perms]
    # MagicMock(name=...) sets the repr name, not the .name attr — set explicitly
    for perm_obj, p in zip(role.permissions, perms):
        perm_obj.name = p
    user.roles = [role]
    return user


def test_access_token_subject_is_string_and_decodes(jwt_app):
    """The sub claim must be a string so PyJWT >= 2.12 accepts it on decode."""
    with jwt_app.app_context():
        user = _fake_user(user_id=7)
        token = create_access_token_for_user(user)

        # decode_token raises "Subject must be a string" if sub is not a str
        decoded = decode_token(token)

        assert isinstance(decoded["sub"], str)
        assert decoded["sub"] == "7"
        # application code converts back to int for DB lookups
        assert int(decoded["sub"]) == 7


def test_access_token_carries_expected_claims(jwt_app):
    with jwt_app.app_context():
        user = _fake_user(user_id=42, username="bob", token_version=5,
                          perms=("series.create", "series.edit"))
        decoded = decode_token(create_access_token_for_user(user))

        assert decoded["userName"] == "bob"
        assert decoded["tokenVersion"] == 5
        assert set(decoded["permissions"]) == {"series.create", "series.edit"}
        assert int(decoded["sub"]) == 42
