from .client import client_and_db, access_token


def test_login_success(client_and_db):
    client, _ = client_and_db
    response = client.post(
        '/login', json={'username': 'admin', 'password': 'admin'})

    assert response.status_code == 200
    assert response.json['msg'] == 'login success'
    assert isinstance(response.json['data'], dict)
    data = response.json['data']

    assert 'accessToken' in data
    assert isinstance(data['accessToken'], str)


def test_login_invalid_request(client_and_db):
    client, _ = client_and_db
    response = client.post('/login', json={})

    assert response.status_code == 400


def test_refresh_token(client_and_db, access_token):
    client, _ = client_and_db

    response = client.post(
        '/jwt/refresh', headers=access_token)

    assert response.status_code == 200
    assert 'accessToken' in response.json
    assert isinstance(response.json['accessToken'], str)
