from unittest.mock import patch, MagicMock
from datetime import datetime
from .client import app
from controller.series import create, read, read_multi, update, delete
from models.series import Field, Series


@patch('models.shared.db.session.add')
@patch('models.shared.db.session.commit')
def test_create_series_success(mock_commit, mock_add, app):
    with app.app_context():
        data = {
            'name': 'Test Series',
            'fields': [
                {'name': 'Field1', 'dataType': 'String', 'isErp': True}
            ]
        }

        create_by = 'user_id'
        response = create(data, create_by)
        json_data = response.get_json()

        assert response.status_code == 201
        assert json_data['code'] == 201
        assert json_data['msg'] == "Success"
        assert 'data' in json_data
        assert json_data['data']['name'] == 'Test Series'


def test_create_series_incomplete_data(app):
    with app.app_context():
        data = {'name': ''}
        create_by = 'user_id'
        response = create(data, create_by)
        json_data = response.get_json()

        assert response.status_code == 400
        assert json_data['code'] == 400
        assert json_data['msg'] == "Incomplete data"


def test_create_series_invalid_data_type(app):
    with app.app_context():
        data = {
            'name': 'Test Series',
            'fields': [
                {'name': 'Field1', 'dataType': 'InvalidType'}
            ]
        }
        create_by = 'user_id'
        response = create(data, create_by)
        json_data = response.get_json()

        assert response.status_code == 400
        assert json_data['code'] == 400
        assert "DataType Error" in json_data['msg']


@patch('models.shared.db.session.query')
def test_read_series_success(session_query_mock, app):
    with app.app_context():
        mock_series = MagicMock()
        mock_series.id = 1
        mock_series.name = 'Test Series'
        mock_series.creator.username = 'creator_user'  # Direct attribute assignment
        mock_series.created_at = datetime.now()

        mock_fields = [
            MagicMock(spec=Field, id=1, name='Field1', data_type='string',
                      is_filtered=True, is_required=False, is_erp=False,
                      is_limit_field=False, sequence=0)
        ]

        # For each field, ensure attributes return serializable data
        for field in mock_fields:
            field.name = 'Field1'
            field.data_type = 'string'
            field.is_filtered = True
            field.is_required = False
            field.is_erp = False
            field.is_limit_field = False
            field.sequence = 0
            # Example list of values
            field.unique_values = ["Value1", "Value2"]

        mock_series.fields = mock_fields

        # Mock the query to return the mock series
        session_query_mock.return_value.filter.return_value.first.return_value = mock_series

        mock_count = MagicMock()
        # Example: Assuming 5 distinct values, adjust as needed
        mock_count.count.return_value = 5

        # Configure session_query_mock for the distinct().count() chain
        session_query_mock.return_value.filter.return_value.distinct.return_value = mock_count

        # Mocking unique_values retrieval
        # Simulate distinct ItemAttribute values
        mock_unique_values = [MagicMock(value="Value1"), MagicMock(
            value="Value2"), MagicMock(value=None)]

        # Configure the mock to return the list for the .all() call
        session_query_mock.return_value.filter.return_value.distinct.return_value.all.return_value = mock_unique_values

        response = read(series_id=1)
        json_data = response.get_json()

        assert response.status_code == 200
        assert json_data['code'] == 200
        assert json_data['msg'] == "Success"
        # Verify the series data, especially that which gets serialized
        assert json_data['data']['id'] == 1
        assert json_data['data']['name'] == 'Test Series'
        # Verify field data
        assert json_data['data']['fields'][0]['name'] == 'Field1'
        assert json_data['data']['fields'][0]['values'] == ["Value1", "Value2"]


@patch('models.shared.db.session.query')
def test_read_series_not_found(session_query_mock, app):
    # Setup mock return value for query to simulate no series found
    mock_query = session_query_mock.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None  # Simulate no series found

    with app.app_context():
        # Use an ID that simulates a missing series
        response = read(series_id=999)
        json_data = response.get_json()

        assert response.status_code == 404
        assert json_data['code'] == 404
        assert json_data['msg'] == "Series not found"


@patch('models.shared.db.session.query')
def test_read_multi_success(session_query_mock, app):
    with app.test_request_context('?page=1&limit=10&showField=1'):
        # You may need to mock other dependencies such as request.args
        # Assuming Series and other necessary dependencies are properly mocked or set up
        mock_series = MagicMock()
        mock_series.id = 1
        mock_series.name = 'Test Series'
        mock_series.creator.username = 'creator_user'  # Direct attribute assignment
        mock_series.created_at = datetime.now()

        mock_fields = [
            MagicMock(spec=Field, id=1, name='Field1', data_type='string',
                      is_filtered=True, is_required=False, is_erp=False,
                      is_limit_field=False, sequence=0)
        ]

        # For each field, ensure attributes return serializable data
        for field in mock_fields:
            field.name = 'Field1'
            field.data_type = 'string'
            field.is_filtered = True
            field.is_required = False
            field.is_erp = False
            field.is_limit_field = False
            field.sequence = 0
            # Example list of values
            field.unique_values = ["Value1", "Value2"]

        mock_series.fields = mock_fields

        # Mocking necessary dependencies such as db.session.query
        # Mocking Series model and its methods
        session_query_mock.return_value.filter_by.return_value.order_by.return_value.count.return_value = 1
        session_query_mock.return_value.filter_by.return_value.order_by.return_value.paginate.return_value.items = [
            mock_series]

        # Simulate the request context with appropriate args
        response = read_multi()
        json_data = response.get_json()

        assert response.status_code == 200
        assert json_data['code'] == 200
        assert json_data['msg'] == "Success"
        # Verify the series data, especially that which gets serialized
        assert json_data['data'][0]['id'] == 1
        assert json_data['data'][0]['name'] == 'Test Series'
        # Verify field data
        assert json_data['data'][0]['fields'][0]['name'] == 'Field1'


@patch('models.shared.db.session.query')
def test_read_multi_incomplete_fields(session_query_mock, app):
    with app.test_request_context('?page=1&limit=10&showField=0'):
        # Assuming Series and other necessary dependencies are properly mocked or set up
        mock_series = MagicMock()
        mock_series.id = 1
        mock_series.name = 'Test Series'
        mock_series.creator.username = 'creator_user'  # Direct attribute assignment
        mock_series.created_at = datetime.now()

        # Mocking only one field, expecting read_multi to return this incomplete data
        mock_fields = [
            MagicMock(spec=Field, id=1, name='Field1', data_type='string',
                      is_filtered=True, is_required=False, is_erp=False,
                      is_limit_field=False, sequence=0)
        ]

        # For each field, ensure attributes return serializable data
        for field in mock_fields:
            field.name = 'Field1'
            field.data_type = 'string'
            field.is_filtered = True
            field.is_required = False
            field.is_erp = False
            field.is_limit_field = False
            field.sequence = 0
            # Example list of values
            field.unique_values = ["Value1", "Value2"]

        mock_series.fields = mock_fields

        # Mocking necessary dependencies such as db.session.query
        # Mocking Series model and its methods
        session_query_mock.return_value.filter_by.return_value.order_by.return_value.count.return_value = 1
        session_query_mock.return_value.filter_by.return_value.order_by.return_value.paginate.return_value.items = [
            mock_series]

        # Simulate the request context with appropriate args
        response = read_multi()
        json_data = response.get_json()

        assert response.status_code == 200
        assert json_data['code'] == 200
        assert json_data['msg'] == "Success"
        # Verify the series data, especially that which gets serialized
        assert json_data['data'][0]['id'] == 1
        assert json_data['data'][0]['name'] == 'Test Series'
        # Verify field data
        # Expecting fields not to be returned when showField is enabled
        assert 'fields' not in json_data['data'][0]


@patch('models.shared.db.session.query')
@patch('models.shared.db.session.get')
def test_update_success(mock_get, mock_query, app):
    with app.app_context():
        # Mock the Series object
        mock_series = MagicMock(spec=Series)
        mock_series.id = 1
        mock_series.name = 'Test Series'

        # Mock the Field object
        mock_field = MagicMock(spec=Field)
        mock_field.id = 1
        mock_field.name = 'Test Field'

        # Configure mock_get to return the appropriate objects
        mock_get.side_effect = [mock_series, mock_field]

        mock_query.return_value.filter_by.return_value.first.return_value = None

        # Prepare test data
        data = {
            'name': 'Updated Series Name',
            'fields': [
                {'id': 1, 'name': 'Updated Field Name', 'dataType': 'string', 'isFiltered': False,
                    'isRequired': True, 'isErp': False, 'isLimitField': False, 'sequence': 0}
            ],
            'create': [],
            'delete': []
        }

        # Call the update function
        response = update(series_id=1, data=data)

        # Assert response status code and message
        assert response.status_code == 200
        assert response.get_json() == {"code": 200, "msg": "Success"}

        # Assert that db.session.get was called with the correct parameters
        mock_get.assert_any_call(Series, 1)
        mock_get.assert_any_call(Field, 1)

        # Assert that series name and field name are updated
        assert mock_series.name == 'Updated Series Name'
        assert mock_field.name == 'Updated Field Name'


@patch('models.shared.db.session.get')
def test_update_series_not_found(mock_get, app):
    with app.app_context():
        # Configure mock_get to return None, simulating Series not found
        mock_get.return_value = None

        # Simulate the request context with appropriate data
        data = {
            'name': 'Updated Series Name',
            'fields': [],
            'create': [],
            'delete': []
        }
        response = update(series_id=1, data=data)

        # Assert response status code and message
        assert response.status_code == 404
        assert response.get_json() == {"code": 404, "msg": "Series not found"}


@patch('models.shared.db.session.query')
@patch('models.shared.db.session.get')
def test_update_with_item_attribute(mock_get, mock_query, app):
    with app.app_context():
        # Mock the necessary dependencies such as db.session.get, db.session.query, etc.
        mock_series = MagicMock()
        mock_series.id = 1
        mock_series.name = 'Test Series'

        # Configure mock_get to return the mock_series
        mock_get.return_value = mock_series

        # Mock the ItemAttribute to simulate related item attributes
        mock_item_attribute = MagicMock()
        mock_query.return_value.filter_by.return_value.first.return_value = mock_item_attribute

        # Simulate the request context with appropriate data
        data = {
            'name': 'Updated Series Name',
            'fields': [
                {'id': 1, 'name': 'Updated Field Name', 'dataType': 'integer', 'isFiltered': False,
                    'isRequired': True, 'isErp': False, 'isLimitField': False, 'sequence': 0}
            ],
            'create': [],
            'delete': []
        }
        response = update(series_id=1, data=data)

        # Assert response status code and message
        assert response.status_code == 400
        assert response.get_json() == {
            "code": 400, "msg": f"Cannot update data type of field with ID 1 since it's being used in ItemAttribute"}


@patch('models.shared.db.session.get')
@patch('models.shared.db.session.commit')
def test_delete_success(mock_commit, mock_get, app):
    with app.app_context():
        # Mock the Series object
        mock_series = MagicMock(spec=Series)
        mock_series.id = 1

        # Configure mock_get to return the mock_series
        mock_get.return_value = mock_series

        # Call the delete function
        response = delete(series_id=1)

        # Assert response status code and message
        assert response.status_code == 200
        assert response.get_json() == {"code": 200, "msg": "Series deleted"}

        # Assert that db.session.get was called with the correct parameters
        mock_get.assert_called_once_with(Series, 1)

        # Assert that series status is set to 0
        assert mock_series.status == 0

        # Assert that db.session.commit was called
        mock_commit.assert_called_once()


@patch('models.shared.db.session.get')
@patch('models.shared.db.session.commit')
def test_delete_series_not_found(mock_commit, mock_get, app):
    with app.app_context():
        # Configure mock_get to return None, simulating series not found
        mock_get.return_value = None

        # Call the delete function
        response = delete(series_id=1)

        # Assert response status code and message
        assert response.status_code == 404
        assert response.get_json() == {"code": 404, "msg": "Series not found"}

        # Assert that db.session.get was called with the correct parameters
        mock_get.assert_called_once_with(Series, 1)

        # Assert that db.session.commit was not called
        assert not mock_commit.called
