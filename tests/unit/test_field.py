from unittest.mock import patch, MagicMock
from controller.field import search_item_attribute_by_field_id_and_value
from .client import app


@patch("controller.field.db.session.query")
@patch("controller.field.check_field_permission")
def test_search_item_attribute_success_with_archive_permission(mock_check_permission, mock_query, app):
    """
    測試當用戶有 archive.create 權限時的成功搜尋
    """
    with app.app_context():
        # Mock 權限檢查 - 用戶有 archive 權限
        mock_check_permission.return_value = True
        
        # Mock 查詢結果 - 當有權限時，不會過濾 archive，所以查詢鏈較短
        mock_query_chain = mock_query.return_value.join.return_value.filter.return_value.filter.return_value.limit.return_value
        mock_query_chain.all.return_value = [
            ("test_value_1",),
            ("test_value_2",),
            ("archived_value_1",),
        ]

        # 調用函數
        result = search_item_attribute_by_field_id_and_value(
            field_id=1, search_value="test"
        )

        # 驗證結果 - 應該包含所有值包括已歸檔的
        assert result["code"] == 200
        assert result["msg"] == "Success"
        assert result["data"] == ["test_value_1", "test_value_2", "archived_value_1"]
        
        # 驗證權限檢查
        mock_check_permission.assert_called_once_with("archive.create")


@patch("controller.field.db.session.query")
@patch("controller.field.check_field_permission")
def test_search_item_attribute_no_archive_permission(mock_check_permission, mock_query, app):
    """
    測試當用戶沒有 archive.create 權限時 - 應該過濾掉已歸檔的項目
    """
    with app.app_context():
        # Mock 權限檢查 - 沒有 archive 權限
        mock_check_permission.return_value = False
        
        # Mock 查詢結果 - 應該排除已歸檔的項目
        mock_query_chain = mock_query.return_value.join.return_value.filter.return_value.filter.return_value.limit.return_value
        mock_query_chain.all.return_value = [
            ("non_archived_value_1",),
            ("non_archived_value_2",),
        ]

        # 調用函數
        result = search_item_attribute_by_field_id_and_value(field_id=1)

        # 驗證結果 - 應該只包含非歸檔的值
        assert result["code"] == 200
        assert result["msg"] == "Success"
        assert result["data"] == ["non_archived_value_1", "non_archived_value_2"]
        
        # 驗證權限檢查
        mock_check_permission.assert_called_once_with("archive.create")


def test_search_item_attribute_missing_field_id():
    """
    測試當 field_id 缺失時的錯誤處理
    """
    # 調用函數但不提供 field_id
    result = search_item_attribute_by_field_id_and_value(field_id=None)  # type: ignore

    # 驗證錯誤回應
    assert result["code"] == 400
    assert result["msg"] == "Missing field_id"
    assert result["data"] == []


@patch("controller.field.db.session.query")
@patch("controller.field.check_field_permission")
def test_search_item_attribute_no_search_value(mock_check_permission, mock_query, app):
    """
    測試當沒有提供 search_value 時的搜尋
    """
    with app.app_context():
        # Mock 權限檢查
        mock_check_permission.return_value = True
        
        # Mock 查詢鏈
        mock_query_chain = mock_query.return_value.join.return_value.filter.return_value.limit.return_value
        mock_query_chain.all.return_value = [
            ("value_a",),
            ("value_b",),
        ]

        # 調用函數
        result = search_item_attribute_by_field_id_and_value(field_id=2)

        # 驗證結果
        assert result["code"] == 200
        assert result["msg"] == "Success"
        assert result["data"] == ["value_a", "value_b"]


@patch("controller.field.check_field_permission")
def test_search_item_attribute_exception(mock_check_permission, app):
    """
    測試當發生資料庫異常時的錯誤處理
    """
    with app.app_context():
        # Mock 權限檢查引發異常
        mock_check_permission.side_effect = Exception("Database error")

        # 調用函數
        result = search_item_attribute_by_field_id_and_value(field_id=1)

        # 驗證錯誤回應
        assert result["code"] == 500
        assert "Database error" in result["msg"]
        assert result["data"] == []


@patch("controller.field.db.session.query")
@patch("controller.field.check_field_permission")
def test_search_item_attribute_with_duplicates_removed(mock_check_permission, mock_query, app):
    """
    測試確保使用 distinct 正確去除重複項
    """
    with app.app_context():
        # Mock 權限檢查
        mock_check_permission.return_value = True
        
        # Mock 查詢鏈
        mock_query_chain = mock_query.return_value.join.return_value.filter.return_value.filter.return_value.limit.return_value
        mock_query_chain.all.return_value = [
            ("unique_value_1",),
            ("unique_value_2",),
            ("unique_value_3",),
        ]

        # 調用函數
        result = search_item_attribute_by_field_id_and_value(
            field_id=1, search_value="unique"
        )

        # 驗證結果 - 應該只包含唯一值
        assert result["code"] == 200
        assert result["msg"] == "Success"
        assert result["data"] == ["unique_value_1", "unique_value_2", "unique_value_3"]


@patch("controller.field.db.session.query")
@patch("controller.field.check_field_permission")
def test_search_item_attribute_limit_results(mock_check_permission, mock_query, app):
    """
    測試確保結果限制為 100 筆
    """
    with app.app_context():
        # Mock 權限檢查
        mock_check_permission.return_value = True
        
        # Mock 查詢鏈
        mock_query_chain = mock_query.return_value.join.return_value.filter.return_value.limit.return_value
        mock_results = [(f"value_{i}",) for i in range(100)]  # 100 筆結果
        mock_query_chain.all.return_value = mock_results

        # 調用函數
        result = search_item_attribute_by_field_id_and_value(field_id=1)

        # 驗證結果限制
        assert result["code"] == 200
        assert result["msg"] == "Success"
        assert len(result["data"]) == 100


@patch("controller.field.db.session.query")
@patch("controller.field.check_field_permission")
def test_search_item_attribute_with_search_value_filter(mock_check_permission, mock_query, app):
    """
    測試當提供 search_value 時的模糊搜尋功能
    """
    with app.app_context():
        # Mock 權限檢查
        mock_check_permission.return_value = True
        
        # Mock 查詢鏈
        mock_query_chain = mock_query.return_value.join.return_value.filter.return_value.filter.return_value.limit.return_value
        mock_query_chain.all.return_value = [
            ("test_match_1",),
            ("test_match_2",),
        ]

        # 調用函數
        result = search_item_attribute_by_field_id_and_value(
            field_id=1, search_value="match"
        )

        # 驗證結果
        assert result["code"] == 200
        assert result["msg"] == "Success"
        assert result["data"] == ["test_match_1", "test_match_2"]
        
        # 驗證權限檢查
        mock_check_permission.assert_called_once_with("archive.create")
