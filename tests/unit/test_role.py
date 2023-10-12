from .client import client_and_db, access_token
from models.user import Permission

created_role_id = None


def test_create_role(client_and_db, access_token):
    client, db = client_and_db

    permission = Permission(name='new_permission')
    db.session.add(permission)
    db.session.commit()

    payload = {
        'roleName': 'newrole',
        'permissionIds': [permission.id]
    }
    response = client.post('/role', json=payload, headers=access_token)

    assert response.status_code == 201
    assert response.json['msg'] == 'Role created'

    global created_role_id
    created_role_id = response.json['data']['id']


def test_get_multiple_roles(client_and_db, access_token):
    client, _ = client_and_db

    # 模擬 GET 請求
    response = client.get('/role', headers=access_token)

    # 斷言回應的狀態碼和內容
    assert response.status_code == 200
    assert response.json['msg'] == 'Roles found'
    assert 'data' in response.json
    assert isinstance(response.json['data'], list)
    data = response.json['data']
    for roles in data:
        assert 'id' in roles
        assert 'name' in roles
        assert 'permissions' in roles
        assert isinstance(roles['permissions'], list)

        for permission in roles['permissions']:
            assert 'id' in permission
            assert 'name' in permission
            assert isinstance(permission['id'], int)
            assert isinstance(permission['name'], str)


def test_get_single_role(client_and_db, access_token):
    client, _ = client_and_db
    role_id = created_role_id

    response = client.get(f'/role/{role_id}', headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Role found'
    assert 'data' in response.json
    assert isinstance(response.json['data'], dict)

    data = response.json['data']

    assert 'id' in data
    assert 'name' in data
    assert 'permissions' in data
    assert isinstance(data['permissions'], list)
    for permission in data['permissions']:
        assert 'id' in permission
        assert 'name' in permission
        assert isinstance(permission['id'], int)
        assert isinstance(permission['name'], str)


def test_update_role(client_and_db, access_token):
    client, _ = client_and_db
    role_id = created_role_id

    payload = {
        'roleName': 'updatedrole',
        'permissionIds': [1, 2, 3, 4, 5, 6, 7]
    }
    response = client.patch(
        f'/role/{role_id}', json=payload, headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Role updated'


def test_delete_role(client_and_db, access_token):
    client, _ = client_and_db
    role_id = created_role_id

    response = client.delete(f'/role/{role_id}', headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Role deleted'
