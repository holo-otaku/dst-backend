import os
import base64
from .client import client_and_db, access_token
from models.series import Series, Field, Item, ItemAttribute


def test_show_logs(client_and_db, access_token):
    client, _ = client_and_db

    response = client.get(
        f'/log', headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Logs found'
    assert 'data' in response.json
    logs = response.json['data']
    assert isinstance(logs, list)

    for log in logs:
        assert 'userId' in log
        assert 'userName' in log
        assert 'url' in log
        assert 'method' in log
        assert 'payload' in log
        assert 'id' in log
        assert 'createdAt' in log

        assert isinstance(log['userId'], int)
        assert isinstance(log['userName'], str)
        assert isinstance(log['url'], str)
        assert isinstance(log['method'], str)
        assert isinstance(log['payload'], object)
        assert isinstance(log['id'], int)
        assert isinstance(log['createdAt'], str)
