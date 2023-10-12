import pytest
from .client import client_and_db, access_token

created_series_id = None


# Create a series
def test_create_series(client_and_db, access_token):
    client, _ = client_and_db
    payload = {
        'name': 'Test Series 1',
        'fields': [
            {
                'id': 10,
                'name': 'Field 1',
                'dataType': 'String',
                'isFiltered': 1,
                'isRequired': 1,
                'isErp': 0,
            },
            {
                'id': 11,
                'name': 'Field 2',
                'dataType': 'Number',
                'isFiltered': 0,
                'isRequired': 0,
                'isErp': 1,
            }
        ]
    }

    response = client.post('/series', json=payload, headers=access_token)

    assert response.status_code == 201
    assert response.json['msg'] == 'Success'
    assert 'data' in response.json
    assert isinstance(response.json['data'], dict)

    global created_series_id
    created_series_id = response.json['data']['id']


# Get multiple series
def test_get_series(client_and_db, access_token):
    client, _ = client_and_db
    response = client.get('/series?showField=1', headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Success'
    assert 'data' in response.json
    assert isinstance(response.json['data'], list)

    data = response.json['data']
    for series in data:
        assert 'createdAt' in series
        assert 'createdBy' in series
        assert 'fields' in series
        assert 'id' in series
        assert 'name' in series

        assert isinstance(series['createdAt'], str)
        assert isinstance(series['createdBy'], str)
        assert isinstance(series['fields'], list)
        assert isinstance(series['id'], int)
        assert isinstance(series['name'], str)


# Get a series
def test_get_single_series(client_and_db, access_token):
    client, _ = client_and_db
    # Assume series_id is known from the previous test or retrieved from the database
    series_id = created_series_id

    response = client.get(f'/series/{series_id}', headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Success'
    assert 'data' in response.json
    assert isinstance(response.json['data'], dict)

    data = response.json['data']
    assert 'createdAt' in data
    assert 'createdBy' in data
    assert 'fields' in data
    assert 'id' in data
    assert 'name' in data

    assert isinstance(data['createdAt'], str)
    assert isinstance(data['createdBy'], str)
    assert isinstance(data['fields'], list)
    assert isinstance(data['id'], int)
    assert isinstance(data['name'], str)

    fields = data['fields']
    assert len(fields) == 2
    assert isinstance(fields, list)
    global update_field_ids
    update_field_ids = []

    for field in fields:
        assert 'id' in field
        assert 'name' in field
        assert 'dataType' in field
        assert 'isFiltered' in field
        assert 'isRequired' in field

        assert isinstance(field['id'], int)
        assert isinstance(field['name'], str)
        assert isinstance(field['dataType'], str)
        assert isinstance(field['isFiltered'], bool)
        assert isinstance(field['isRequired'], bool)
        assert isinstance(field['isErp'], bool)

        update_field_ids.append(field)

# Update a series


def test_update_series(client_and_db, access_token):
    client, _ = client_and_db
    # Assume series_id is known from the previous test or retrieved from the database
    series_id = created_series_id

    payload = {
        'name': 'Updated Series',
        'fields': [],
        "create": [
            {
                "name": "美金",
                "dataType": "boolean",
                "isFiltered": False,
                "isRequired": False,
                "isErp": False,
                "sequence": 3,
            }
        ]
    }

    for field in update_field_ids:
        payload['fields'].append(field)

    response = client.patch(
        f'/series/{series_id}', json=payload, headers=access_token)

    assert response.json['msg'] == 'Success'
    assert response.status_code == 200


# Delete a series
def test_delete_series(client_and_db, access_token):
    client, _ = client_and_db
    # Assume series_id is known from the previous test or retrieved from the database
    series_id = created_series_id

    response = client.delete(f'/series/{series_id}', headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Series deleted'
