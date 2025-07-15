from unittest.mock import patch, MagicMock
from controller.field import search_item_attribute_by_field_id_and_value
from .client import app


def test_search_item_attribute_success(app):
    """
    Test case for successful search.
    """
    with app.app_context():
        with patch("controller.field.ItemAttribute.query") as mock_query:
            # Mock the query and its results
            mock_item1 = MagicMock()
            mock_item1.value = "test_value_1"
            mock_item2 = MagicMock()
            mock_item2.value = "test_value_2"
            mock_query.filter.return_value.filter.return_value.limit.return_value.all.return_value = [
                mock_item1,
                mock_item2,
            ]

            # Call the function
            result = search_item_attribute_by_field_id_and_value(
                field_id=1, search_value="test"
            )

            # Assert the result
            assert result["code"] == 200
            assert result["msg"] == "Success"
            assert result["data"] == ["test_value_1", "test_value_2"]


def test_search_item_attribute_missing_field_id():
    """
    Test case for when field_id is missing.
    """
    # Call the function with no field_id
    result = search_item_attribute_by_field_id_and_value(field_id=None)

    # Assert the error response
    assert result["code"] == 400
    assert result["msg"] == "Missing field_id"
    assert result["data"] == []


def test_search_item_attribute_no_search_value(app):
    """
    Test case for when search_value is not provided.
    """
    with app.app_context():
        with patch("controller.field.ItemAttribute.query") as mock_query:
            # Mock the query and its results
            mock_item1 = MagicMock()
            mock_item1.value = "value_a"
            mock_item2 = MagicMock()
            mock_item2.value = "value_b"
            mock_query.filter.return_value.limit.return_value.all.return_value = [
                mock_item1,
                mock_item2,
            ]

            # Call the function
            result = search_item_attribute_by_field_id_and_value(field_id=2)

            # Assert the result
            assert result["code"] == 200
            assert result["msg"] == "Success"
            assert result["data"] == ["value_a", "value_b"]


def test_search_item_attribute_exception(app):
    """
    Test case for when a database exception occurs.
    """
    with app.app_context():
        with patch("controller.field.ItemAttribute.query") as mock_query:
            # Configure the mock to raise an exception
            mock_query.filter.side_effect = Exception("Database error")

            # Call the function
            result = search_item_attribute_by_field_id_and_value(field_id=1)

            # Assert the error response
            assert result["code"] == 500
            assert "Database error" in result["msg"]
            assert result["data"] == []