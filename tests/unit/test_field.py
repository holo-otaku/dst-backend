from unittest.mock import patch, MagicMock
from controller.field import search_item_attribute_by_field_id_and_value
from .client import app


@patch("controller.field.db.session.query")
def test_search_item_attribute_success(mock_query, app):
    """
    Test case for successful search.
    """
    with app.app_context():
        # Mock the query results - results are tuples since we're using distinct
        mock_query.return_value.filter.return_value.limit.return_value.all.return_value = [
            ("test_value_1",),
            ("test_value_2",),
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
    # Call the function with no field_id - using type: ignore for testing purposes
    result = search_item_attribute_by_field_id_and_value(field_id=None)  # type: ignore

    # Assert the error response
    assert result["code"] == 400
    assert result["msg"] == "Missing field_id"
    assert result["data"] == []


@patch("controller.field.db.session.query")
def test_search_item_attribute_no_search_value(mock_query, app):
    """
    Test case for when search_value is not provided.
    """
    with app.app_context():
        # Mock the query results - results are tuples since we're using distinct
        mock_query.return_value.filter.return_value.limit.return_value.all.return_value = [
            ("value_a",),
            ("value_b",),
        ]

        # Call the function
        result = search_item_attribute_by_field_id_and_value(field_id=2)

        # Assert the result
        assert result["code"] == 200
        assert result["msg"] == "Success"
        assert result["data"] == ["value_a", "value_b"]


@patch("controller.field.db.session.query")
def test_search_item_attribute_exception(mock_query, app):
    """
    Test case for when a database exception occurs.
    """
    with app.app_context():
        # Configure the mock to raise an exception
        mock_query.side_effect = Exception("Database error")

        # Call the function
        result = search_item_attribute_by_field_id_and_value(field_id=1)

        # Assert the error response
        assert result["code"] == 500
        assert "Database error" in result["msg"]
        assert result["data"] == []


@patch("controller.field.db.session.query")
def test_search_item_attribute_with_duplicates_removed(mock_query, app):
    """
    Test case to ensure duplicates are properly removed using distinct.
    """
    with app.app_context():
        # Mock query results with what would be duplicate values
        mock_query.return_value.filter.return_value.limit.return_value.all.return_value = [
            ("unique_value_1",),
            ("unique_value_2",),
            ("unique_value_3",),
        ]

        # Call the function
        result = search_item_attribute_by_field_id_and_value(
            field_id=1, search_value="unique"
        )

        # Assert the result - should only contain unique values
        assert result["code"] == 200
        assert result["msg"] == "Success"
        assert result["data"] == ["unique_value_1", "unique_value_2", "unique_value_3"]
        assert len(result["data"]) == len(set(result["data"]))  # Ensure no duplicates


@patch("controller.field.db.session.query")
def test_search_item_attribute_limit_results(mock_query, app):
    """
    Test case to ensure results are limited to 100.
    """
    with app.app_context():
        # Mock query that would return many results
        mock_results = [(f"value_{i}",) for i in range(150)]  # 150 results
        mock_query.return_value.filter.return_value.limit.return_value.all.return_value = mock_results[:100]  # But limited to 100

        # Call the function
        result = search_item_attribute_by_field_id_and_value(field_id=1)

        # Assert the result is limited
        assert result["code"] == 200
        assert result["msg"] == "Success"
        assert len(result["data"]) == 100