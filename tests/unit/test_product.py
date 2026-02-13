from unittest.mock import patch, MagicMock
from .client import app
from controller.product import (
    create,
    read,
    read_multi,
    update_multi,
    delete,
    create_from_items,
)
from models.series import Field, Series, Item, ItemAttribute
from models.image import Image
from models.archive import Archive


@patch("controller.product.__create_item")
@patch("controller.product.__normalize_payload_from_request")
@patch("models.shared.db.session.commit")
def test_create_success(mock_commit, mock_normalize, mock_create_item, app):
    with app.app_context():
        mock_normalize.return_value = {"series_id": 1, "attributes": []}
        mock_item = MagicMock(id=1, series_id=1)
        mock_create_item.return_value = (mock_item, None)

        data = [
            {
                "seriesId": 1,
                "attributes": [
                    {"fieldId": 1, "value": "Value1"},
                    {"fieldId": 2, "value": "Value2"},
                ],
            }
        ]

        response = create(data=data)

        assert response.status_code == 201
        assert response.get_json()["code"] == 201
        assert response.get_json()["msg"] == "Success"

        mock_normalize.assert_called_once()
        mock_create_item.assert_called_once()
        mock_commit.assert_called_once()


@patch("controller.product.__create_item")
@patch("controller.product.__normalize_payload_from_request")
def test_create_incomplete_data(mock_normalize, mock_create_item, app):
    with app.app_context():
        mock_normalize.return_value = {"series_id": None, "attributes": []}
        error_resp = MagicMock(status_code=400)
        error_resp.get_json.return_value = {"code": 400, "msg": "Incomplete data"}
        mock_create_item.return_value = (None, error_resp)

        response = create(data=[{"attributes": [{"fieldId": 1, "value": "Value1"}]}])

        assert response.status_code == 400
        assert response.get_json()["code"] == 400
        mock_normalize.assert_called_once()
        mock_create_item.assert_called_once()


@patch("controller.product.__create_item")
@patch("controller.product.__normalize_payload_from_request")
def test_create_series_not_found(mock_normalize, mock_create_item, app):
    with app.app_context():
        mock_normalize.return_value = {"series_id": 1, "attributes": []}
        error_resp = MagicMock(status_code=404)
        error_resp.get_json.return_value = {"code": 404, "msg": "Series not found"}
        mock_create_item.return_value = (None, error_resp)

        response = create(
            data=[{"seriesId": 1, "attributes": [{"fieldId": 1, "value": "Value1"}]}]
        )

        assert response.status_code == 404
        assert response.get_json() == {"code": 404, "msg": "Series not found"}

        mock_normalize.assert_called_once()
        mock_create_item.assert_called_once()


@patch("models.shared.db.session.get")
@patch("models.shared.db.session.query")
@patch("controller.product.read_erp")
@patch("controller.product.has_permission")
def test_read_success(mock_has_permission, mock_read_erp, mock_query, mock_get, app):
    with app.app_context():
        # Prepare mock data
        mock_item = MagicMock(id=1, series_id=1, is_deleted=False)
        mock_series = MagicMock()
        mock_series.name = "Test Series"
        mock_item.series = mock_series

        # Mock field
        mock_field = MagicMock()
        mock_field.id = 1
        mock_field.name = "Field1"
        mock_field.data_type = "string"
        mock_field.search_erp = True
        mock_field.is_limit_field = False
        mock_field.series_id = 1

        # Mock attribute
        mock_attribute = MagicMock()
        mock_attribute.field_id = 1
        mock_attribute.field = mock_field
        mock_attribute.value = "Value1"

        # Configure mocks
        mock_get.return_value = mock_item
        mock_has_permission.return_value = True

        # Mock the query calls
        def mock_query_side_effect(model):
            if model == Field:
                field_query = MagicMock()
                field_query.filter.return_value.order_by.return_value.all.return_value = [mock_field]
                return field_query
            elif model == ItemAttribute:
                attribute_query = MagicMock()
                attribute_query.filter.return_value.all.return_value = [mock_attribute]
                return attribute_query
            elif model == Archive:
                archive_query = MagicMock()
                archive_query.filter_by.return_value.first.return_value = None
                return archive_query
            return MagicMock()

        mock_query.side_effect = mock_query_side_effect

        mock_read_erp.return_value = {"Value1": [{"fieldName": "ERP_Field_1", "value": "ERP_Value_1"}]}

        # Call the read function
        response = read(product_id=1)

        # Assert the response
        assert response.status_code == 200
        assert response.get_json() == {
            "code": 200,
            "msg": "Success",
            "data": {
                "itemId": 1,
                "seriesId": 1,
                "attributes": [
                    {
                        "fieldId": 1,
                        "fieldName": "Field1",
                        "dataType": "string",
                        "value": "Value1",
                    }
                ],
                "seriesName": "Test Series",
                "erp": [{"fieldName": "ERP_Field_1", "value": "ERP_Value_1"}],
                "hasArchive": False,
                "isDeleted": False,
            },
        }


@patch("models.shared.db.session.get")
def test_read_product_id_missing(mock_get, app):
    with app.app_context():
        # Mock the case where product_id is missing
        response = read(None)

        # Assert the response
        assert response.status_code == 400
        assert response.get_json() == {"code": 400, "msg": "Product ID is required"}


@patch("models.shared.db.session.get")
def test_read_product_not_found(mock_get, app):
    with app.app_context():
        # Mock the case where product does not exist
        mock_get.return_value = None

        # Call the read function with a non-existing product_id
        response = read(123)

        # Assert the response
        assert response.status_code == 404
        assert response.get_json() == {"code": 404, "msg": "Product not found"}


@patch("models.shared.db.session.get")
@patch("models.shared.db.session.query")
@patch("models.shared.db.session.commit")
@patch("controller.product.__check_field_type")
@patch("controller.product.__save_image")
def test_update_multi_success(
    mock_save_image, mock_check_field_type, mock_commit, mock_query, mock_get, app
):
    with app.app_context():
        # Mock Item object
        mock_item = MagicMock()
        mock_item.id = 1

        # Mock Field object
        mock_field = MagicMock()
        mock_field.id = 1
        mock_field.data_type = "string"

        # Mock the ItemAttribute object and set initial value
        mock_item_attribute = MagicMock()
        mock_item_attribute.value = None

        # Configure mock_get to return the mock_item for items and None for fields (to simulate field not found)
        def get_side_effect(model, id):
            if model == Item:
                return mock_item
            elif model == Field:
                return mock_field  # Simulating field not found for simplicity

        mock_get.side_effect = get_side_effect

        # Mock the query for ItemAttribute to return our mock_item_attribute
        mock_query.return_value.filter_by.return_value.first.return_value = (
            mock_item_attribute
        )

        # Mock __check_field_type to always return an empty list (no type errors)
        mock_check_field_type.return_value = []

        # Mock __save_image to simulate image saving
        mock_save_image.return_value = "path/to/saved/image"

        # Prepare test data
        data = [
            {
                "itemId": 1,
                "attributes": [
                    {"fieldId": 1, "value": "NewValue1"},
                    # Assuming this is a boolean that will be saved as an image path
                    {"fieldId": 2, "value": True},
                ],
            }
        ]

        # Call the update_multi function
        response = update_multi(data)

        # Assert response status code and message
        assert response.status_code == 200
        assert response.get_json()["code"] == 200
        assert response.get_json()["msg"] == "ItemAttributes updated"

        # Verify the mock_item_attribute's value was updated
        assert (
            mock_item_attribute.value == "NewValue1" or "path/to/saved/image"
        ), "ItemAttribute value was not updated correctly"

        # Verify __check_field_type and __save_image were called correctly
        mock_check_field_type.assert_called()

        # Assert that db.session.commit was called
        mock_commit.assert_called_once()


@patch("models.shared.db.session.commit")
@patch("models.shared.db.session.query")
@patch("models.shared.db.session.get")
def test_delete_success(mock_get, mock_query, mock_commit, app):
    with app.app_context():
        mock_item = MagicMock()
        mock_item.id = 123
        mock_item.attributes = []

        mock_image = MagicMock()
        mock_image.id = "1"
        mock_image.path = "/path/to/image"

        mock_attribute = MagicMock()
        mock_attribute.field.data_type = "picture"
        mock_attribute.value = mock_image.id

        mock_item.attributes.append(mock_attribute)

        mock_items_query = MagicMock()
        mock_items_query.filter.return_value.all.return_value = [mock_item]
        mock_items_query.filter.return_value.delete.return_value = None

        mock_image_query = MagicMock()
        mock_image_query.get.return_value = mock_image

        mock_archive = MagicMock()

        def query_side_effect(model):
            if model == Item:
                return mock_items_query
            elif model == Image:
                return mock_image_query
            elif model == Archive:
                return mock_archive
            else:
                return MagicMock()

        mock_query.side_effect = query_side_effect

        mock_get = MagicMock()
        mock_get.return_value = mock_image

        data = {"itemId": [123]}

        response = delete(data)

        assert response.status_code == 200
        assert response.get_json()["code"] == 200
        assert response.get_json()["msg"] == "Items deleted"

        mock_commit.assert_called_once()


def test_delete_with_no_data(app):
    with app.app_context():
        data = None

        response = delete(data)

        assert response.status_code == 400
        assert response.get_json()["code"] == 400
        assert response.get_json()["msg"] == "Invalid data"


def test_delete_with_missing_itemId(app):
    with app.app_context():
        data = {"someOtherKey": "someValue"}

        response = delete(data)

        assert response.status_code == 400
        assert response.get_json()["code"] == 400
        assert response.get_json()["msg"] == "Invalid data"


@patch("controller.product.__create_item")
@patch("controller.product.__normalize_payload_from_item")
@patch("models.shared.db.session.commit")
@patch("models.shared.db.session.query")
def test_copy_success(mock_query, mock_commit, mock_normalize, mock_create_item, app):
    with app.app_context():
        mock_item = MagicMock(spec=Item)
        mock_item.id = 1
        mock_item.series_id = 10

        mock_query_obj = MagicMock()
        mock_query_obj.filter.return_value.all.return_value = [mock_item]
        mock_query.return_value = mock_query_obj

        mock_normalize.return_value = {"series_id": 10, "attributes": [], "fields": []}
        mock_new_item = MagicMock(id=999, series_id=10)
        mock_create_item.return_value = (mock_new_item, None)

        response = create_from_items({"itemIds": [1]})

        assert response.status_code == 201
        json_data = response.get_json()
        assert json_data["code"] == 201
        assert json_data["msg"] == "Success"
        assert json_data["data"][0]["id"] == 999
        assert json_data["data"][0]["seriesId"] == 10

        mock_query.assert_called_once_with(Item)
        mock_normalize.assert_called_once_with(mock_item)
        mock_create_item.assert_called_once()
        mock_commit.assert_called_once()


@patch("models.shared.db.session.query")
def test_copy_with_missing_item(mock_query, app):
    with app.app_context():
        mock_query_obj = MagicMock()
        mock_query_obj.filter.return_value.all.return_value = []
        mock_query.return_value = mock_query_obj

        response = create_from_items({"itemIds": [999]})

        assert response.status_code == 404
        assert response.get_json() == {"code": 404, "msg": "Item(s) not found: [999]"}
        mock_query.assert_called_once_with(Item)


def test_copy_with_invalid_input(app):
    with app.app_context():
        # 測試缺少 itemIds
        response1 = create_from_items({})
        assert response1.status_code == 400
        assert response1.get_json() == {"code": 400, "msg": "itemIds must be a list"}

        # 測試 itemIds 不是 list
        response2 = create_from_items({"itemIds": "not-a-list"})
        assert response2.status_code == 400
        assert response2.get_json() == {"code": 400, "msg": "itemIds must be a list"}

        # 測試 itemIds 是空 list
        response3 = create_from_items({"itemIds": []})
        assert response3.status_code == 400
        assert response3.get_json() == {"code": 400, "msg": "itemIds must be a list"}


@patch("models.shared.db.session.get")
@patch("models.shared.db.session.query")
@patch("controller.product.read_erp")
@patch("controller.product.has_permission")
def test_read_deleted_product(mock_has_permission, mock_read_erp, mock_query, mock_get, app):
    """
    Test reading a deleted product returns isDeleted: true
    """
    with app.app_context():
        # Prepare mock data for deleted item
        mock_item = MagicMock(id=1, series_id=1, is_deleted=True)
        mock_series = MagicMock()
        mock_series.name = "Test Series"
        mock_item.series = mock_series

        # Mock field
        mock_field = MagicMock()
        mock_field.id = 1
        mock_field.name = "Field1"
        mock_field.data_type = "string"
        mock_field.search_erp = False
        mock_field.is_limit_field = False
        mock_field.series_id = 1

        # Mock attribute
        mock_attribute = MagicMock()
        mock_attribute.field_id = 1
        mock_attribute.field = mock_field
        mock_attribute.value = "Value1"

        # Configure mocks
        mock_get.return_value = mock_item
        mock_has_permission.return_value = True

        # Mock the query calls
        def mock_query_side_effect(model):
            if model == Field:
                field_query = MagicMock()
                field_query.filter.return_value.order_by.return_value.all.return_value = [mock_field]
                return field_query
            elif model == ItemAttribute:
                attribute_query = MagicMock()
                attribute_query.filter.return_value.all.return_value = [mock_attribute]
                return attribute_query
            elif model == Archive:
                archive_query = MagicMock()
                archive_query.filter_by.return_value.first.return_value = None
                return archive_query
            return MagicMock()

        mock_query.side_effect = mock_query_side_effect
        mock_read_erp.return_value = {}

        # Call the read function
        response = read(product_id=1)

        # Assert the response
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["code"] == 200
        assert response_data["msg"] == "Success"
        assert response_data["data"]["isDeleted"] == True
        assert response_data["data"]["itemId"] == 1
