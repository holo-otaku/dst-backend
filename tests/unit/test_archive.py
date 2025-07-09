from unittest.mock import patch, MagicMock
from models.archive import Archive
from controller.archive import create, delete
from .client import app


@patch("controller.archive.get_jwt_identity", return_value=1)
@patch("models.shared.db.session.add")
@patch("models.shared.db.session.commit")
def test_create_archives_success(mock_commit, mock_add, mock_jwt, app):
    with app.test_request_context():
        from controller.archive import Archive

        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.side_effect = [None, MagicMock()]

        with patch.object(Archive, "query", new=mock_query):
            data = {"itemIds": [101, 102]}
            response = create(data)

            assert response.status_code == 200
            res = response.get_json()
            assert res["code"] == 200
            assert res["data"]["skipped"] == [102]


@patch("controller.archive.get_jwt_identity", return_value=1)
def test_create_no_item_ids(mock_jwt, app):
    with app.test_request_context():
        from controller.archive import create

        data = {}  # 沒有 itemIds
        response = create(data)

        assert response.status_code == 400
        res = response.get_json()
        assert res["code"] == 400
        assert res["msg"] == "No itemIds provided"


@patch("models.shared.db.session.delete")
@patch("models.shared.db.session.commit")
def test_delete_archives_success(mock_commit, mock_delete, app):
    with app.test_request_context():
        from controller.archive import Archive, delete

        mock_query = MagicMock()
        mock_query.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=MagicMock())),  # item 201 存在
            MagicMock(first=MagicMock(return_value=None)),  # item 202 不存在
        ]

        with patch.object(Archive, "query", new=mock_query):
            data = {"itemIds": [201, 202]}
            response = delete(data)

            assert response.status_code == 200
            res = response.get_json()
            assert res["code"] == 200
            assert res["data"]["deleted"] == [201]
            assert res["data"]["notFound"] == [202]


def test_delete_no_item_ids(app):
    with app.test_request_context():
        from controller.archive import delete

        data = {}  # 缺少 itemIds
        response = delete(data)

        assert response.status_code == 400
        res = response.get_json()
        assert res["code"] == 400
        assert res["msg"] == "No itemIds provided"
