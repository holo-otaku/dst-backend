from .client import client_and_db, access_token
from models.series import Item
from .test_product import create_item


def test_create_archive(client_and_db, access_token):
    client, db = client_and_db

    _, series_id = create_item(db)

    item = Item(series_id=series_id)
    db.session.add(item)
    db.session.commit()

    item = db.session.query(Item).first()

    payload = {"itemId": item.id}
    response = client.post(
        f'/archive', json=payload, headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Success'


def test_delete_archive(client_and_db, access_token):
    client, _ = client_and_db

    response = client.delete(
        f'/archive/1', headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Success'
