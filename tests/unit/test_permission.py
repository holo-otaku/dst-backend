from .client import client_and_db, access_token

created_permission_id = None


def test_create_permission(client_and_db, access_token):
    client, _ = client_and_db
    payload = {
        'name': 'test'
    }

    response = client.post('/permission', json=payload, headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Permission created'

    global created_permission_id
    created_permission_id = response.json['data']['id']


def test_get_multiple_permissions(client_and_db, access_token):
    client, _ = client_and_db

    # 使用新增的权限ID进行测试
    permission_id = created_permission_id

    response = client.get('/permission', headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Permission found'
    assert 'data' in response.json
    assert isinstance(response.json['data'], list)

    data = response.json['data']
    for permission in data:
        assert 'id' in permission
        assert 'name' in permission

        assert isinstance(permission['id'], int)
        assert isinstance(permission['name'], str)


def test_get_single_permission(client_and_db, access_token):
    client, _ = client_and_db

    # 使用新增的权限ID进行测试
    permission_id = created_permission_id

    response = client.get(f'/permission/{permission_id}', headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Permission found'
    assert 'data' in response.json

    permission = response.json['data']

    assert 'id' in permission
    assert 'name' in permission

    assert isinstance(permission['id'], int)
    assert isinstance(permission['name'], str)


def test_update_permission(client_and_db, access_token):
    client, _ = client_and_db

    permission_id = created_permission_id
    payload = {
        'name': 'test 1'
    }

    response = client.patch(
        f'/permission/{permission_id}', json=payload, headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Permission updated'


def test_delete_permission(client_and_db, access_token):
    client, _ = client_and_db

    # 使用新增的权限ID进行测试
    permission_id = created_permission_id

    response = client.delete(
        f'/permission/{permission_id}', headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Permission deleted'
