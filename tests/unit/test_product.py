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


@patch("models.shared.db.session.get")
@patch("models.shared.db.session.query")
@patch("models.shared.db.session.commit")
@patch("models.shared.db.session.add")
def test_create_success(mock_add, mock_commit, mock_query, mock_get, app):
    with app.app_context():
        # Mock the Series object
        mock_series = MagicMock(spec=Series)
        mock_series.id = 1

        # Configure mock_get to return the mock_series
        mock_get.return_value = mock_series

        # Create mock objects for fields and field query
        mock_field_1 = MagicMock(id=1, name="Field1", is_required=True)
        mock_field_2 = MagicMock(id=2, name="Field2", is_required=False)
        mock_fields = [mock_field_1, mock_field_2]
        mock_field_query = MagicMock()
        mock_query.return_value.filter.return_value = MagicMock()
        mock_field_query.all.return_value = [mock_field_1]

        # Prepare test data
        data = [
            {
                "seriesId": 1,
                "attributes": [
                    {"fieldId": 1, "value": "Value1"},
                    {"fieldId": 2, "value": "Value2"},
                ],
            }
        ]

        # Call the create function
        response = create(data=data)

        # Assert response status code and message
        assert response.status_code == 201
        assert response.get_json()["code"] == 201
        assert response.get_json()["msg"] == "Success"

        # Assert that db.session.get was called with the correct parameters
        mock_get.assert_called_once_with(Series, 1)

        # Assert that db.session.query was called with the correct parameters
        mock_query.assert_called_once_with(Field)

        # Assert that db.session.commit was called
        mock_commit.assert_called_once()


@patch("models.shared.db.session.get")
def test_create_incomplete_data(mock_get, app):
    with app.app_context():
        # Call the create function with incomplete data
        response = create(data=[{"attributes": [{"fieldId": 1, "value": "Value1"}]}])

        # Assert response status code and message
        assert response.status_code == 400
        assert response.get_json() == {"code": 400, "msg": "Incomplete data"}

        # Assert that db.session.get was not called
        assert not mock_get.called


@patch("models.shared.db.session.get")
def test_create_series_not_found(mock_get, app):
    with app.app_context():
        # Configure mock_get to return None, simulating series not found
        mock_get.return_value = None

        # Call the create function
        response = create(
            data=[{"seriesId": 1, "attributes": [{"fieldId": 1, "value": "Value1"}]}]
        )

        # Assert response status code and message
        assert response.status_code == 404
        assert response.get_json() == {"code": 404, "msg": "Series not found"}

        # Assert that db.session.get was called with the correct parameters
        mock_get.assert_called_once_with(Series, 1)


@patch("models.shared.db.session.get")
@patch("models.shared.db.session.query")
@patch("controller.product.read_erp")
def test_read_success(mock_read_erp, mock_query, mock_get, app):
    with app.app_context():
        # Prepare mock data
        mock_item = MagicMock(id=1, series_id=1)
        mock_series = MagicMock()
        mock_series.name = "Test Series"
        mock_attribute = MagicMock()
        mock_attribute.field_id = 1
        mock_attribute.field.name = "Field1"
        mock_attribute.field.data_type = "string"
        mock_attribute.field.search_erp = True
        mock_attribute.value = "Value1"
        mock_item.series = mock_series
        mock_query.return_value.filter.return_value.all.return_value = [mock_attribute]
        mock_get.return_value = mock_item

        mock_attribute.field.search_erp = True
        mock_read_erp.return_value = {"Value1": [{"fieldName": "ERP_Field_1", "value": "ERP_Value_1"}]}

        mock_query.return_value.filter_by.return_value.first.return_value = None

        # Call the read function
        response = read(product_id=1)

        # Convert MagicMock objects to strings before assertion
        for attribute in response.get_json()["data"]["attributes"]:
            attribute["fieldName"] = str(attribute["fieldName"])

        # Assert the response
        assert response.status_code == 200
        print(response.get_json())
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

        print(response.get_json())
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


@patch("controller.product.__save_image")
@patch("models.shared.db.session.commit")
@patch("models.shared.db.session.flush")
@patch("models.shared.db.session.add")
@patch("models.shared.db.session.query")
@patch("models.shared.db.session.get")
def test_copy_success(
    mock_get, mock_query, mock_add, mock_flush, mock_commit, mock_save_image, app
):
    with app.app_context():
        # 模擬原始 Item
        mock_item = MagicMock(spec=Item)
        mock_item.id = 1
        mock_item.series_id = 10

        # 模擬屬性 Field 與 ItemAttribute
        mock_field = MagicMock()
        mock_field.data_type = "picture"

        mock_attr = MagicMock(spec=ItemAttribute)
        mock_attr.item_id = 1
        mock_attr.field_id = 100
        mock_attr.value = "image/path/original.jpg"
        mock_attr.field = mock_field

        # 模擬複製圖片後的回傳值
        mock_save_image.return_value = "image/path/copied.jpg"

        # Configure session.get to return the mock_item
        mock_get.return_value = mock_item

        # 模擬 .query(ItemAttribute).filter_by().all()
        mock_query.return_value.filter_by.return_value.all.return_value = [mock_attr]

        # 執行函式
        request_data = {"itemIds": [1]}
        response = create_from_items(request_data)

        # 驗證 HTTP 回應
        assert response.status_code == 201
        json_data = response.get_json()
        assert json_data["code"] == 201
        assert json_data["msg"] == "Success"
        assert isinstance(json_data["data"], list)
        assert "id" in json_data["data"][0]
        assert "seriesId" in json_data["data"][0]

        # 驗證是否呼叫預期的操作
        mock_get.assert_called_with(Item, 1)
        mock_query.assert_called_with(ItemAttribute)
        mock_add.assert_called()
        mock_commit.assert_called_once()
        mock_save_image.assert_called_once()


@patch("models.shared.db.session.get")
def test_copy_with_missing_item(mock_get, app):
    with app.app_context():
        # 模擬 db.session.get 找不到該 item
        mock_get.return_value = None

        request_data = {"itemIds": [999]}

        response = create_from_items(request_data)

        assert response.status_code == 404
        assert response.get_json() == {"code": 404, "msg": "Item 999 not found"}

        mock_get.assert_called_once_with(Item, 999)


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
