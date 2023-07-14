from .client import client_and_db, access_token

created_user_id = None


def test_create_user(client_and_db, access_token):
    client, db = client_and_db
    # 模擬 POST 請求
    payload = {
        'username': 'testuser',
        'password': 'password',
        'roleId': 1
    }
    response = client.post('/user', json=payload, headers=access_token)

    # 斷言回應的狀態碼和內容
    assert response.status_code == 201
    assert response.json['msg'] == 'Success'
    assert 'data' in response.json
    assert isinstance(response.json['data'], dict)

    global created_user_id
    created_user_id = response.json['data']['id']


def test_get_multiple_users(client_and_db, access_token):
    client, _ = client_and_db
    # 模擬 GET 請求
    response = client.get('/user', headers=access_token)

    # 斷言回應的狀態碼和內容
    assert response.status_code == 200
    assert response.json['msg'] == 'Success'
    assert 'data' in response.json
    assert isinstance(response.json['data'], list)


def test_get_single_user(client_and_db, access_token):
    client, _ = client_and_db
    # 假設已經存在特定 ID 的使用者 user_id
    user_id = created_user_id

    # 模擬 GET 請求
    response = client.get(f'/user/{user_id}', headers=access_token)

    # 斷言回應的狀態碼和內容
    assert response.status_code == 200
    assert response.json['msg'] == 'Success'
    assert 'data' in response.json
    assert isinstance(response.json['data'], dict)


def test_update_user(client_and_db, access_token):
    client, _ = client_and_db
    # 假設已經存在特定 ID 的使用者 user_id
    user_id = created_user_id

    # 模擬 PATCH 請求
    payload = {
        'username': 'updateduser',
        'password': 'updatedpassword',
        'roleId': 1
    }
    response = client.patch(
        f'/user/{user_id}', json=payload, headers=access_token)

    # 斷言回應的狀態碼和內容
    assert response.status_code == 200
    assert response.json['msg'] == 'Success'
    assert 'data' in response.json
    assert isinstance(response.json['data'], dict)


def test_delete_user(client_and_db, access_token):
    client, _ = client_and_db
    # 假設已經存在特定 ID 的使用者 user_id
    user_id = created_user_id

    # 模擬 DELETE 請求
    response = client.delete(f'/user/{user_id}', headers=access_token)

    # 斷言回應的狀態碼和內容
    assert response.status_code == 200
    assert response.json['msg'] == 'User deleted'
