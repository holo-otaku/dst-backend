import os
import base64
from .client import client_and_db, access_token
from models.series import Series, Field, Item, ItemAttribute
# Create a product
created_product_id = None


def test_create_product(client_and_db, access_token):
    client, db = client_and_db

    # 创建 Series 实例
    series = Series(
        name='Test Series',
        created_by=1,
    )

    # 创建 Field 实例
    field1 = Field(
        name='Field 1',
        data_type='String',
        is_required=False,
        is_filtered=True,
    )
    field2 = Field(
        name='Field 2',
        data_type='Number',
        is_required=True,
        is_filtered=False,
    )

    field3 = Field(
        name='Field 3',
        data_type='Boolean',
        is_required=True,
        is_filtered=False,
    )

    field4 = Field(
        name='Field 4',
        data_type='Picture',
        is_required=True,
        is_filtered=False,
    )

    # 将 Field 实例关联到 Series 实例
    series.fields = [field1, field2, field3, field4]

    # 添加 Series 和 Field 实例到数据库
    db.session.add(series)
    db.session.add(field1)
    db.session.add(field2)
    db.session.add(field3)
    db.session.add(field4)
    db.session.commit()

    # Sample image file path (replace with your actual image file path)
    image_file_path = './tests/test.png'

    # Get the absolute path of the image file
    image_file_path = os.path.abspath(image_file_path)

    # Read the image file as bytes
    with open(image_file_path, 'rb') as image_file:
        image_bytes = image_file.read()

    # Encode the image bytes as a base64 string
    image_base64 = base64.b64encode(image_bytes).decode()

    payload = [
        {
            "seriesId": series.id,
            "name": "Product 1",
            "attributes": [
                {
                    "fieldId": field1.id,
                    "value": "Value 1"
                },
                {
                    "fieldId": field2.id,
                    "value": 5
                },
                {
                    "fieldId": field3.id,
                    "value": True
                },
                {
                    "fieldId": field4.id,
                    "value": image_base64
                }
            ]
        }
    ]

    response = client.post('/product', json=payload, headers=access_token)

    assert response.json['msg'] == 'Success'
    assert response.status_code == 201
    assert 'data' in response.json
    assert isinstance(response.json['data'], list)
    data = response.json['data']

    for product in data:
        assert isinstance(product, dict)

        assert 'id' in product
        assert 'name' in product
        assert 'seriesId' in product

        assert isinstance(product['id'], int)
        assert isinstance(product['name'], str)
        assert isinstance(product['seriesId'], int)

    global created_product_id
    created_product_id = response.json['data'][0]['id']


def test_show_products(client_and_db, access_token):
    client, _ = client_and_db

    product_id = created_product_id

    response = client.get(
        f'/product/{product_id}', headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Success'
    assert 'data' in response.json
    assert 'attributes' in response.json['data']
    attributes = response.json['data']['attributes']
    assert isinstance(attributes, list)

    for attribute in attributes:
        assert 'fieldId' in attribute
        assert 'value' in attribute

        assert isinstance(attribute['fieldId'], int)
        assert isinstance(attribute['value'], str)
# Search products in a series


# def test_search_products(client_and_db, access_token):
#     client, _ = client_and_db

#     series_id = 1
#     payload = [
#         {
#             "fieldId": 1,
#             "value": "Value 1",
#             "operation": "equals"
#         },
#         {
#             "fieldId": 2,
#             "value": 5,
#         }
#     ]

#     response = client.post(
#         f'/product/{series_id}/search', json=payload, headers=access_token)

#     assert response.status_code == 200
#     assert response.json['msg'] == 'Success'
#     assert 'data' in response.json
#     assert isinstance(response.json['data'], list)

# Edit products


def test_edit_products(client_and_db, access_token):
    client, _ = client_and_db

    product_id = created_product_id

    payload = [
        {
            "itemId": product_id,
            "name": "Updated Product",
            "attributes": [
                {
                    "fieldId": 1,
                    "value": "Updated Value"
                }
            ]
        }
    ]

    response = client.patch(
        '/product/edit', json=payload, headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'ItemAttributes updated'

# Delete products


def test_delete_products(client_and_db, access_token):
    client, _ = client_and_db

    product_id = created_product_id

    payload = {
        "itemId": [product_id]
    }

    response = client.delete(
        '/product/delete', json=payload, headers=access_token)

    assert response.status_code == 200
    assert response.json['msg'] == 'Items deleted'
