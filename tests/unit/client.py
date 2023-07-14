from controller.user import create_admin_user
from controller.role import create_admin_role
from controller.permission import create_default_permissions
import pytest
from test import create_app


@pytest.fixture(scope='session')
def client_and_db():
    app, db = create_app()
    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            create_default_permissions()
            create_admin_role()
            create_admin_user()

        yield client, db

        db.drop_all()


@pytest.fixture(scope='session')
def access_token(client_and_db):
    client, _ = client_and_db

    login_response = client.post(
        '/login', json={'username': 'admin', 'password': 'admin'})
    assert login_response.status_code == 200

    access_token = login_response.json['data']['accessToken']
    headers = {'Authorization': f'Bearer {access_token}'}

    return headers
