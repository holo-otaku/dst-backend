import jwt as pyjwt
from flask_jwt_extended import JWTManager
from middlewares.token_version import TokenVersionMiddleware
from tests.unit.client import app  # noqa: F401


def test_legacy_token_forces_logout(app):
    app.config['JWT_SECRET_KEY'] = 'test-secret-key-that-is-long-enough-32b'
    JWTManager(app)
    TokenVersionMiddleware(app)
    app.add_url_rule('/ping', 'ping', lambda: 'ok')

    # 舊版 token：sub 為 int，新版 PyJWT 會拒絕
    token = pyjwt.encode({'sub': 1, 'type': 'access'}, app.config['JWT_SECRET_KEY'], algorithm='HS256')
    res = app.test_client().get('/ping', headers={'Authorization': f'Bearer {token}'})

    assert res.status_code == 401
    assert res.get_json()['forceLogout'] is True
