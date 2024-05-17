from unittest.mock import patch, MagicMock, PropertyMock
from controller.user import create, read, read_multi, update, delete
from models.user import User, Role
from .client import app


@patch('models.shared.db.session.commit', autospec=True)
@patch('models.shared.db.session.add', autospec=True)
@patch('models.shared.db.session.get', autospec=True)
def test_create_user(mock_get, mock_add, mock_commit, app):
    with app.app_context():
        # Create a simple mock role with necessary attributes
        mock_role = MagicMock(spec=Role)
        mock_role.id = 1
        mock_role.name = 'Admin'
        # Ensure the mock has the _sa_instance_state attribute, if necessary
        mock_role._sa_instance_state = MagicMock()
        mock_get.return_value = mock_role

        payload = {'username': 'admin', 'password': 'dstadmin', 'roleId': 1}

        response = create(payload)
        assert response.status_code == 201
        # Assuming the response is a Flask Response object
        data = response.get_json()  # This is how you should access JSON data

        # Now you can assert on data directly
        assert data is not None
        assert 'code' in data
        assert 'msg' in data
        assert 'data' in data
        assert isinstance(data['code'], int)
        assert isinstance(data['msg'], str)
        assert isinstance(data['data'], object)
        assert data['code'] == 200
        assert data['msg'] == 'Success'

        assert 'id' in data['data']
        assert 'username' in data['data']
        assert 'role' in data['data']


@patch('models.shared.db.session.commit', autospec=True)
@patch('models.shared.db.session.add', autospec=True)
@patch('models.shared.db.session.get', autospec=True)
def test_create_user_incomplete(mock_get, mock_add, mock_commit, app):
    with app.app_context():
        # Create a simple mock role with necessary attributes
        mock_role = MagicMock(spec=Role)
        mock_role.id = 1
        mock_role.name = 'Admin'
        # Ensure the mock has the _sa_instance_state attribute, if necessary
        mock_role._sa_instance_state = MagicMock()
        mock_get.return_value = mock_role

        payload = {'password': 'dstadmin', 'roleId': 1}
        response = create(payload)
        assert response.status_code == 400
        data = response.get_json()  # This is how you should access JSON data
        assert 'code' in data
        assert 'msg' in data
        assert data['code'] == 200
        assert data['msg'] == 'Incomplete data'


@patch('models.shared.db.session.get', autospec=True)
def test_read_user_found(mock_get, app):
    with app.app_context():
        # Mock user
        mock_user = MagicMock(spec=User)
        mock_user.username = 'testuser'

        # Mock roles attribute to return a list of objects with serializable attributes
        role_mock = MagicMock()
        type(role_mock).name = PropertyMock(return_value='Admin')
        type(role_mock).id = PropertyMock(return_value=1)

        mock_user.roles = [role_mock]

        mock_get.return_value = mock_user

        response = read(user_id=1)
        data = response.get_json()

        assert response.status_code == 200
        assert data['code'] == 200
        assert data['msg'] == "Success"
        assert data['data']['userName'] == 'testuser'
        assert data['data']['role'] == 'Admin'
        assert data['data']['roleId'] == 1


@patch('models.shared.db.session.get', autospec=True)
def test_read_user_not_found(mock_get, app):
    with app.app_context():
        mock_get.return_value = None

        response = read(user_id=99)  # Assuming 99 is an ID that does not exist
        data = response.get_json()

        assert response.status_code == 404
        assert data['code'] == 200
        assert data['msg'] == "User not found"


@patch('models.shared.db.session.query')  # Mock User.query
def test_read_multi_success(mock_query, app):
    with app.test_request_context('?page=1&limit=2'):
        # Setup the mock query to return users with serializable roles
        mock_user_query = mock_query.return_value
        # Create mocked users with roles that have a serializable 'name' attribute
        mock_user_1 = MagicMock(id=1, username='User1')
        role_1 = MagicMock()
        role_name_1 = PropertyMock(return_value='Role1')
        type(role_1).name = role_name_1
        mock_user_1.roles = [role_1]
        mock_user_2 = MagicMock(id=2, username='User2')
        mock_user_2.roles = []  # An empty list for users without roles
        mock_user_query.limit.return_value.offset.return_value.all.return_value = [
            mock_user_1, mock_user_2]
        mock_user_query.count.return_value = 2

        # Call the function under test
        response = read_multi()
        data = response.get_json()

        assert response.status_code == 200

        # Assertions
        expected_result = [{'id': 1, 'userName': 'User1', 'role': 'Role1'}, {
            'id': 2, 'userName': 'User2', 'role': None}]

        assert data == {"code": 200, "msg": "Success",
                        "data": expected_result, "totalCount": 2}


@patch('models.shared.db.session.query')  # Mock db.session.query
def test_read_multi_failure(mock_query, app):
    with app.test_request_context('?page=1&limit=2'):
        # Setup the mock query to raise an exception when trying to fetch users
        mock_query.side_effect = Exception("Database query failed")

        # Call the function under test
        response = read_multi()
        data = response.get_json()

        # Assertions for failure scenario
        # Assuming 500 is the status code for internal errors
        assert response.status_code == 500
        # Assuming your application uses the same status code in the response body
        assert data['code'] == 500
        # Assuming the error message contains the word "error"Ｆ
        assert 'failed' in data['msg'].lower()

        # Mock the User and Role model, and db session


@patch('models.shared.db.session.get', side_effect=lambda model, id: model(id=id) if model.__name__ == "User" else None)
def test_update_user_success(mock_db_get, app):
    with app.app_context():
        # Create a mocked user object with a roles list
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "OldUsername"
        mock_user.roles = []

        # Use side_effect or return_value to simulate the behavior of set_password and roles' operations
        mock_user.set_password = MagicMock()

        # Instead of mocking roles.clear or roles.append directly,
        # you could manipulate the roles list directly in your test and verify it as needed
        def append_role(role):
            mock_user.roles.append(role)

        def clear_roles():
            mock_user.roles.clear()

        mock_role = MagicMock()
        mock_role.id = 2
        role_name_property = PropertyMock(return_value='NewRole')
        type(mock_role).name = role_name_property

        # In your actual test function, after invoking the update operation:
        append_role(mock_role)  # Simulate adding a role
        assert mock_role in mock_user.roles  # Verify the role was added

        clear_roles()  # Simulate clearing roles
        assert not mock_user.roles  # Verify the roles are cleared

        def db_get_side_effect(model, id):
            if model == User and id == 1:
                return mock_user
            elif model == Role and id == 2:
                return mock_role
            return None

        mock_db_get.side_effect = db_get_side_effect

        # Test data for update
        user_id = 1  # Existing user ID
        update_data = {'username': 'NewUsername',
                       'password': 'newpassword', 'roleId': 2}

        # Call the update function
        response = update(user_id, update_data)
        data = response.get_json()

        # Assertions
        assert response.status_code == 200
        assert data['code'] == 200
        assert data['msg'] == "Success"
        assert data['data']['username'] == "NewUsername"
        assert data['data']['role'] == "NewRole"
        # Verify that user's information was updated
        mock_user.set_password.assert_called_with('newpassword')


# Assuming your Flask app and update function are correctly imported
@patch('models.shared.db.session.get', return_value=None)
def test_update_user_not_found(mock_db_get, app):
    with app.app_context():
        user_id = 99  # Non-existent user ID
        update_data = {'username': 'NewUsername'}

        # Call the update function
        response = update(user_id, update_data)
        data = response.get_json()

        # Assertions for user not found scenario
        assert response.status_code == 404
        assert data == {"code": 400, "msg": "User not found"}


@patch('models.shared.db.session.get')
def test_update_user_invalid_role(mock_db_get, app):
    with app.app_context():
        # Mock user exists, but role does not
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "ExistingUsername"
        mock_db_get.side_effect = lambda model, id: mock_user if model.__name__ == "User" else None

        user_id = 1  # Existing user ID
        update_data = {'roleId': 999, 'password': "123"}  # Invalid role ID

        # Call the update function
        response = update(user_id, update_data)
        data = response.get_json()

        # Assertions for invalid role scenario
        assert response.status_code == 400
        assert data == {"code": 400, "msg": "Invalid role"}


@patch('models.shared.db.session.get')
def test_update_user_invalid_password(mock_db_get, app):
    with app.app_context():
        # Mock user exists, but role does not
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "ExistingUsername"
        mock_db_get.side_effect = lambda model, id: mock_user if model.__name__ == "User" else None

        user_id = 1  # Existing user ID
        update_data = {'roleId': 1, 'password': ""}

        # Call the update function
        response = update(user_id, update_data)
        data = response.get_json()

        # Assertions for invalid role scenario
        assert response.status_code == 400
        assert data == {"code": 400, "msg": "Invalid password: "}


# Test case for successful user deletion
@patch('models.shared.db.session.commit')
@patch('models.shared.db.session.delete')
@patch('models.shared.db.session.get')
def test_delete_user_success(mock_db_get, mock_db_delete, mock_db_commit, app):
    with app.app_context():
        mock_user = MagicMock()
        mock_db_get.return_value = mock_user  # Simulate finding the user

        user_id = 1  # Example user ID
        response = delete(user_id)
        data = response.get_json()

        mock_db_get.assert_called_once_with(User, user_id)
        mock_db_delete.assert_called_once_with(mock_user)
        mock_db_commit.assert_called_once()
        assert response.status_code == 200
        assert data == {"code": 200, "msg": "User deleted"}

# Test case for user not found


@patch('models.shared.db.session.get')
def test_delete_user_not_found(mock_db_get, app):
    with app.app_context():
        mock_db_get.return_value = None  # Simulate user not found

        user_id = 99  # Example user ID that does not exist
        response = delete(user_id)
        data = response.get_json()

        mock_db_get.assert_called_once_with(User, user_id)
        assert response.status_code == 404
        assert data == {"code": 200, "msg": "User not found"}
