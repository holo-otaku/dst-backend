from unittest.mock import patch, MagicMock
from datetime import datetime
from .client import app
from controller.series import create, read, read_multi, update, delete
from models.series import Field, Series


@patch("models.shared.db.session.add")
@patch("models.shared.db.session.commit")
def test_create_series_success(mock_commit, mock_add, app):
    with app.app_context():
        data = {
            "name": "Test Series",
            "fields": [{"name": "Field1", "dataType": "String", "searchErp": True}],
        }

        create_by = "user_id"
        response = create(data, create_by)
        json_data = response.get_json()

        assert response.status_code == 201
        assert json_data["code"] == 201
        assert json_data["msg"] == "Success"
        assert "data" in json_data
        assert json_data["data"]["name"] == "Test Series"


def test_create_series_incomplete_data(app):
    with app.app_context():
        data = {"name": ""}
        create_by = "user_id"
        response = create(data, create_by)
        json_data = response.get_json()

        assert response.status_code == 400
        assert json_data["code"] == 400
        assert json_data["msg"] == "Incomplete data"


def test_create_series_invalid_data_type(app):
    with app.app_context():
        data = {
            "name": "Test Series",
            "fields": [{"name": "Field1", "dataType": "InvalidType"}],
        }
        create_by = "user_id"
        response = create(data, create_by)
        json_data = response.get_json()

        assert response.status_code == 400
        assert json_data["code"] == 400
        assert "DataType Error" in json_data["msg"]


from unittest.mock import patch, MagicMock
from datetime import datetime


from unittest.mock import patch, MagicMock
from datetime import datetime


@patch("controller.series.get_erp_fields_metadata")
@patch("models.shared.db.session.query")
def test_read_series_success(session_query_mock, mock_get_erp_fields_metadata, app):
    with app.app_context():
        mock_series = MagicMock()
        mock_series.id = 1
        mock_series.name = "Test Series"
        mock_series.creator = MagicMock()
        mock_series.creator.username = "creator_user"
        mock_series.created_at = datetime.now()

        # 非 ERP 欄位，但 search_erp=True（這是關鍵，會觸發 has_search_erp=True）
        trigger_field = MagicMock()
        trigger_field.id = 3
        trigger_field.name = "TriggerField"
        trigger_field.data_type = "string"
        trigger_field.is_filtered = False
        trigger_field.is_required = False
        trigger_field.search_erp = True  # 🔑
        trigger_field.is_limit_field = False
        trigger_field.sequence = 2
        trigger_field.is_erp = False
        trigger_field.unique_values = []

        # ERP 欄位
        field2 = MagicMock()
        field2.id = 2
        field2.name = "ERP_Field"
        field2.data_type = "string"
        field2.is_filtered = False
        field2.is_required = False
        field2.search_erp = True
        field2.is_limit_field = True
        field2.sequence = 1
        field2.is_erp = True
        field2.unique_values = []

        # 一般欄位
        field1 = MagicMock()
        field1.id = 1
        field1.name = "Field1"
        field1.data_type = "string"
        field1.is_filtered = True
        field1.is_required = False
        field1.search_erp = False
        field1.is_limit_field = False
        field1.sequence = 0
        field1.is_erp = False
        field1.unique_values = ["Value1", "Value2"]

        mock_series.fields = [field1, field2, trigger_field]

        # 模擬查詢 series
        session_query_mock.return_value.filter.return_value.first.return_value = (
            mock_series
        )

        # 模擬 distinct count 和 values
        mock_distinct = (
            session_query_mock.return_value.filter.return_value.distinct.return_value
        )
        mock_distinct.count.return_value = 2
        mock_distinct.all.return_value = [
            MagicMock(value="Value1"),
            MagicMock(value="Value2"),
        ]

        # 模擬 ERP metadata 回傳
        mock_get_erp_fields_metadata.return_value = [
            {"name": "ERP_Field", "dataType": "string"}
        ]

        response = read(series_id=1)
        json_data = response.get_json()

        assert response.status_code == 200
        assert json_data["code"] == 200
        assert json_data["msg"] == "Success"
        assert json_data["data"]["id"] == 1
        assert json_data["data"]["name"] == "Test Series"

        # 確認 fields 都有出現
        field_names = [f["name"] for f in json_data["data"]["fields"]]
        assert "Field1" in field_names
        assert "ERP_Field" in field_names
        assert "TriggerField" in field_names


@patch("models.shared.db.session.query")
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
        assert json_data["code"] == 404
        assert json_data["msg"] == "Series not found"


@patch("models.shared.db.session.query")
def test_read_multi_success(session_query_mock, app):
    with app.test_request_context("?page=1&limit=10&showField=1"):
        # You may need to mock other dependencies such as request.args
        # Assuming Series and other necessary dependencies are properly mocked or set up
        mock_series = MagicMock()
        mock_series.id = 1
        mock_series.name = "Test Series"
        mock_series.creator = MagicMock(
            username="creator_user"
        )  # Mock the creator object
        mock_series.created_at = datetime.now()

        mock_fields = [
            MagicMock(
                id=1,
                name="Field1",
                data_type="string",
                is_filtered=True,
                is_required=False,
                search_erp=False,
                is_limit_field=False,
                sequence=0,
                is_erp=False,
            )
        ]

        # For each field, ensure attributes return serializable data
        for field in mock_fields:
            field.name = "Field1"
            field.data_type = "string"
            field.is_filtered = True
            field.is_required = False
            field.search_erp = False
            field.is_limit_field = False
            field.sequence = 0
            # Example list of values
            field.unique_values = ["Value1", "Value2"]

        mock_series.fields = mock_fields

        # Mocking necessary dependencies such as db.session.query
        # Mocking Series model and its methods
        session_query_mock.return_value.filter_by.return_value.order_by.return_value.count.return_value = (
            1
        )
        session_query_mock.return_value.filter_by.return_value.order_by.return_value.paginate.return_value.items = [
            mock_series
        ]

        # Simulate the request context with appropriate args
        response = read_multi()
        json_data = response.get_json()

        assert response.status_code == 200
        assert json_data["code"] == 200
        assert json_data["msg"] == "Success"
        # Verify the series data, especially that which gets serialized
        assert json_data["data"][0]["id"] == 1
        assert json_data["data"][0]["name"] == "Test Series"
        # Verify field data
        assert json_data["data"][0]["fields"][0]["name"] == "Field1"


@patch("models.shared.db.session.query")
def test_read_multi_incomplete_fields(session_query_mock, app):
    with app.test_request_context("?page=1&limit=10&showField=0"):
        # Assuming Series and other necessary dependencies are properly mocked or set up
        mock_series = MagicMock()
        mock_series.id = 1
        mock_series.name = "Test Series"
        mock_series.creator = MagicMock(
            username="creator_user"
        )  # Direct attribute assignment
        mock_series.created_at = datetime.now()

        # Mocking only one field, expecting read_multi to return this incomplete data
        mock_fields = [
            MagicMock(
                id=1,
                name="Field1",
                data_type="string",
                is_filtered=True,
                is_required=False,
                search_erp=False,
                is_limit_field=False,
                sequence=0,
            )
        ]

        # For each field, ensure attributes return serializable data
        for field in mock_fields:
            field.name = "Field1"
            field.data_type = "string"
            field.is_filtered = True
            field.is_required = False
            field.search_erp = False
            field.is_limit_field = False
            field.sequence = 0
            # Example list of values
            field.unique_values = ["Value1", "Value2"]

        mock_series.fields = mock_fields

        # Mocking necessary dependencies such as db.session.query
        # Mocking Series model and its methods
        session_query_mock.return_value.filter_by.return_value.order_by.return_value.count.return_value = (
            1
        )
        session_query_mock.return_value.filter_by.return_value.order_by.return_value.paginate.return_value.items = [
            mock_series
        ]

        # Simulate the request context with appropriate args
        response = read_multi()
        json_data = response.get_json()

        assert response.status_code == 200
        assert json_data["code"] == 200
        assert json_data["msg"] == "Success"
        # Verify the series data, especially that which gets serialized
        assert json_data["data"][0]["id"] == 1
        assert json_data["data"][0]["name"] == "Test Series"
        # Verify field data
        # Expecting fields not to be returned when showField is enabled
        assert "fields" not in json_data["data"][0]


@patch("models.shared.db.session.query")
@patch("models.shared.db.session.get")
def test_update_success(mock_get, mock_query, app):
    with app.app_context():
        # Mock the Series object
        mock_series = MagicMock()
        mock_series.id = 1
        mock_series.name = "Test Series"

        # Mock the Field object
        mock_field = MagicMock()
        mock_field.id = 1
        mock_field.name = "Test Field"

        # Configure mock_get to return the appropriate objects
        mock_get.side_effect = [mock_series, mock_field]

        mock_query.return_value.filter_by.return_value.first.return_value = None

        # Prepare test data
        data = {
            "name": "Updated Series Name",
            "fields": [
                {
                    "id": 1,
                    "name": "Updated Field Name",
                    "dataType": "string",
                    "isFiltered": False,
                    "isRequired": True,
                    "searchErp": False,
                    "isLimitField": False,
                    "sequence": 0,
                }
            ],
            "create": [],
            "delete": [],
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
        assert mock_series.name == "Updated Series Name"
        assert mock_field.name == "Updated Field Name"


@patch("models.shared.db.session.get")
def test_update_series_not_found(mock_get, app):
    with app.app_context():
        # Configure mock_get to return None, simulating Series not found
        mock_get.return_value = None

        # Simulate the request context with appropriate data
        data = {"name": "Updated Series Name", "fields": [], "create": [], "delete": []}
        response = update(series_id=1, data=data)

        # Assert response status code and message
        assert response.status_code == 404
        assert response.get_json() == {"code": 404, "msg": "Series not found"}


@patch("models.shared.db.session.query")
@patch("models.shared.db.session.get")
def test_update_with_item_attribute(mock_get, mock_query, app):
    with app.app_context():
        # Mock the necessary dependencies such as db.session.get, db.session.query, etc.
        mock_series = MagicMock()
        mock_series.id = 1
        mock_series.name = "Test Series"

        # Configure mock_get to return the mock_series
        mock_get.return_value = mock_series

        # Mock the ItemAttribute to simulate related item attributes
        mock_item_attribute = MagicMock()
        mock_query.return_value.filter_by.return_value.first.return_value = (
            mock_item_attribute
        )

        # Simulate the request context with appropriate data
        data = {
            "name": "Updated Series Name",
            "fields": [
                {
                    "id": 1,
                    "name": "Updated Field Name",
                    "dataType": "integer",
                    "isFiltered": False,
                    "isRequired": True,
                    "searchErp": False,
                    "isLimitField": False,
                    "sequence": 0,
                }
            ],
            "create": [],
            "delete": [],
        }
        response = update(series_id=1, data=data)

        # Assert response status code and message
        assert response.status_code == 400
        assert response.get_json() == {
            "code": 400,
            "msg": f"Cannot update data type of field '{mock_series.name}' as it is in use.",
        }


@patch("models.shared.db.session.get")
@patch("models.shared.db.session.commit")
def test_delete_success(mock_commit, mock_get, app):
    with app.app_context():
        # Mock the Series object
        mock_series = MagicMock()
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


@patch("models.shared.db.session.get")
@patch("models.shared.db.session.commit")
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
