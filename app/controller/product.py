from flask import current_app, jsonify, make_response, request
from models.series import *
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, text
import math

# Mapping of field data types to Python data types
data_type_map = {
    'string': str,
    'number': (int, float),
    'boolean': bool,
    # Add other data types as needed
}


def create(data):
    try:
        items = []

        for item_data in data:
            series_id = item_data.get('seriesId')
            name = item_data.get('name')
            attributes = item_data.get('attributes')

            if not series_id or not name or not attributes:
                return make_response(jsonify({"code": 400, "msg": "Incomplete data"}), 400)

            series = Series.query.get(series_id)
            if not series:
                return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

            item = Item(series_id=series_id, name=name)
            db.session.add(item)

            for attribute in attributes:
                field_id = attribute.get('fieldId')
                value = attribute.get('value')

                field = Field.query.get(field_id)
                if not field:
                    return make_response(jsonify({"code": 400, "msg": f"Invalid field_id: {field_id}"}), 400)

                item_attribute = ItemAttribute(
                    item_id=item.id, field_id=field_id, value=value)
                db.session.add(item_attribute)

            items.append(item)

        db.session.commit()

        result = [{'id': item.id, 'name': item.name,
                   'seriesId': item.series_id} for item in items]
        return make_response(jsonify({"code": 201, "msg": "Success", "data": result}), 201)

    except SQLAlchemyError as e:
        db.session.rollback()
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read(series_id):
    try:
        # Extract the filter criteria from the request body
        filters = request.json
        # Ensure the series_id is an integer
        series_id = int(series_id)

        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        # Get the fields related to this series
        fields_query = db.session.query(Field).filter(
            Field.series_id == series_id)
        fields = {field.id: field for field in fields_query.all()}

        # Check if all required fields are in the request body
        required_fields_query = fields_query.filter(Field.is_required == True)
        required_fields = {
            field.id: field for field in required_fields_query.all()}
        for required_field_id in required_fields.keys():
            if not any(filter.get('fieldId') == required_field_id for filter in filters):
                return make_response(jsonify({"code": 400,
                                              "msg": f"Missing required field: {required_fields[required_field_id].name}"}), 400)

        # Create a SQL query to find the items
        sql_query = """
            SELECT item.id AS item_id,
                item.series_id AS item_series_id,
                item.name AS item_name
            FROM item
            WHERE item.series_id = :series_id
                AND (
        """

        conditions = []
        parameters = {'series_id': series_id}

        for filter_criteria in filters:
            field_id = filter_criteria['fieldId']
            value = filter_criteria['value']
            operation = filter_criteria.get('operation', 'equals')

            # Check if the value is of the correct data type
            field = fields[field_id]
            correct_type = data_type_map[field.data_type.lower()]
            if not isinstance(value, correct_type):
                return make_response(jsonify({
                    "code": 400,
                    "msg": f"Incorrect data type for field: {field.name}. Expected {field.data_type.lower()}, got {type(value).__name__}."
                }), 400)

            condition = f"""
                (item.id, item.series_id, item.name) IN (
                    SELECT DISTINCT item.id,
                                    item.series_id,
                                    item.name
                    FROM item
                        JOIN item_attribute ON item.id = item_attribute.item_id
                    WHERE item.series_id = :series_id
                        AND item_attribute.field_id = {field_id}
                        AND item_attribute.value = '{value}'
                )
            """
            if operation == 'greater' and field.data_type.lower() == 'number':
                condition = f"""
                (item.id, item.series_id, item.name) IN (
                    SELECT DISTINCT item.id,
                                    item.series_id,
                                    item.name
                    FROM item
                        JOIN item_attribute ON item.id = item_attribute.item_id
                    WHERE item.series_id = :series_id
                        AND item_attribute.field_id = {field_id}
                        AND CAST(item_attribute.value AS float) > {value}
                )
                """
            elif operation == 'less' and field.data_type.lower() == 'number':
                condition = f"""
                (item.id, item.series_id, item.name) IN (
                    SELECT DISTINCT item.id,
                                    item.series_id,
                                    item.name
                    FROM item
                        JOIN item_attribute ON item.id = item_attribute.item_id
                    WHERE item.series_id = :series_id
                        AND item_attribute.field_id = {field_id}
                        AND CAST(item_attribute.value AS float) < {value}
                )
                """

            conditions.append(condition)

        sql_query += " AND ".join(conditions)
        sql_query += ")"

        # Execute the SQL query
        result = db.session.execute(text(sql_query), parameters).fetchall()

        # Paginate the results
        paginated_result = result[(page-1)*limit: page*limit]

        # Format the output
        data = []
        for row in paginated_result:
            item_id, item_series_id, item_name = row
            fields_data = {field.id: db.session.query(ItemAttribute).filter(
                and_(ItemAttribute.item_id == item_id,
                     ItemAttribute.field_id == field.id)
            ).first().value for field in fields.values()}
            data.append({
                'itemId': item_id,
                'name': item_name,
                'seriesId': item_series_id,
                'fields': fields_data
            })

        return make_response(jsonify({"code": 200, "msg": "Success", "data": data}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def edit(data):
    try:
        # 檢查輸入資料的完整性
        if not data:
            return make_response(jsonify({'code': 400, 'msg': 'Empty data'}), 400)

        # 建立一個暫存字典來存放要編輯的 ItemAttribute
        item_attributes = {}

        # 遍歷每個輸入項目
        for item_data in data:
            item_id = item_data.get('itemId')
            name = item_data.get('name')
            attributes = item_data.get('attributes')

            # 檢查輸入項目的完整性
            if not item_id or not name or not attributes:
                return make_response(jsonify({'code': 400, 'msg': 'Incomplete data'}), 400)

            # 查詢對應的 Item 記錄
            item = Item.query.get(item_id)

            # 檢查 Item 是否存在
            if not item:
                return make_response(jsonify({'code': 404, 'msg': 'Item not found'}), 404)

            # 更新 Item 的 name
            item.name = name

            # 遍歷每個屬性
            for attribute in attributes:
                field_id = attribute.get('fieldId')
                value = attribute.get('value')

                # 檢查屬性的完整性
                if not field_id or not value:
                    return make_response(jsonify({'code': 400, 'msg': 'Incomplete attribute data'}), 400)

                # 查詢對應的 Field 記錄
                field = Field.query.get(field_id)

                # 檢查 Field 是否存在且 data_type 符合預期
                if not field or not isinstance(value, data_type_map[field.data_type.lower()]):
                    return make_response(jsonify({'code': 400, 'msg': f'Invalid data type for fieldId: {field_id}'}), 400)

                # 將要編輯的 ItemAttribute 存入暫存字典
                if item_id not in item_attributes:
                    item_attributes[item_id] = {}
                item_attributes[item_id][field_id] = value

        # 根據暫存字典進行批量編輯
        for item_id, attribute_values in item_attributes.items():
            for field_id, value in attribute_values.items():
                # 查詢對應的 ItemAttribute 記錄
                item_attribute = ItemAttribute.query.filter_by(
                    item_id=item_id, field_id=field_id).first()

                # 檢查是否找到對應的記錄
                if item_attribute:
                    # 更新 value 值
                    item_attribute.value = value

        # 儲存變更到資料庫
        db.session.commit()

        # 回傳成功訊息
        return make_response(jsonify({'code': 200, 'msg': 'ItemAttributes updated'}), 200)

    except Exception as e:
        # 處理例外情況，回滾交易並回傳錯誤訊息
        db.session.rollback()
        return make_response(jsonify({'code': 500, 'msg': str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        # 確保關閉資料庫連線
        db.session.close()


def delete(data):
    try:
        # 檢查輸入資料的完整性
        if not data or 'itemId' not in data:
            return make_response(jsonify({'code': 400, 'msg': 'Invalid data'}), 400)

        # 獲取要刪除的 Item IDs
        item_ids = data['itemId']

        # 查詢要刪除的 Item 記錄
        items = Item.query.filter(Item.id.in_(item_ids)).all()

        # 檢查是否找到對應的 Item 記錄
        if not items:
            return make_response(jsonify({'code': 404, 'msg': 'Items not found'}), 404)

        # 批次刪除 Item 記錄
        db.session.query(Item).filter(Item.id.in_(item_ids)
                                      ).delete(synchronize_session=False)

        # 批次刪除 ItemAttribute 記錄
        db.session.query(ItemAttribute).filter(
            ItemAttribute.item_id.in_(item_ids)).delete(synchronize_session=False)

        # 儲存變更到資料庫
        db.session.commit()

        # 回傳成功訊息
        return make_response(jsonify({'code': 200, 'msg': 'Items deleted'}), 200)

    except Exception as e:
        # 處理例外情況，回滾交易並回傳錯誤訊息
        db.session.rollback()
        return make_response(jsonify({'code': 500, 'msg': str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        # 確保關閉資料庫連線
        db.session.close()
