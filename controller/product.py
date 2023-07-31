from flask import current_app, jsonify, make_response, request
from controller.erp import read as read_erp
from models.series import Series, Field, Item, ItemAttribute
from models.shared import db
from models.mapping_table import data_type_map
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, text
from datetime import datetime


def show(product_id):
    try:
        # Check if product_id is provided
        if not product_id:
            return make_response(jsonify({"code": 400, "msg": "Product ID is required"}), 400)

        # Get the item related to this product_id
        item = db.session.get(Item, product_id)

        # Check if product exists
        if not item:
            return make_response(jsonify({"code": 404, "msg": "Product not found"}), 404)

        # Get the attributes related to this product
        attributes_query = db.session.query(ItemAttribute).filter(
            ItemAttribute.item_id == product_id)

        # Format attributes
        attributes = [{"fieldId": attribute.field_id, "value": attribute.value}
                      for attribute in attributes_query.all()]

        # Format the output
        result = {
            "itemId": item.id,
            "name": item.name,
            "seriesId": item.series_id,
            "attributes": attributes
        }

        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def create(data):
    try:
        items = []

        for item_data in data:
            series_id = item_data.get('seriesId')
            name = item_data.get('name')
            attributes = item_data.get('attributes')

            # Get the fields related to this series
            fields_query = db.session.query(Field).filter(
                Field.series_id == series_id)

            if not series_id or not name or not attributes:
                return make_response(jsonify({"code": 400, "msg": "Incomplete data"}), 400)

            series = db.session.get(Series, series_id)

            if not series:
                return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

            item = Item(series_id=series_id, name=name)
            db.session.add(item)

            missing_field = __check_field_required(
                fields_query, attributes, Field.is_required)

            if (len(missing_field) != 0):
                return make_response(jsonify({"code": 400,
                                              "msg": f"Missing required field: {missing_field}"}), 400)

            for attribute in attributes:
                field_id = attribute.get('fieldId')
                value = attribute.get('value')

                field = db.session.get(Field, field_id)
                if not field:
                    return make_response(jsonify({"code": 400, "msg": f"Invalid field_id: {field_id}"}), 400)

                # Check if the value is of the correct data type
                type_err = __check_field_type(field, value)
                if (len(type_err) != 0):
                    return make_response(jsonify({
                        "code": 400,
                        "msg": type_err
                    }), 400)

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


def read():
    try:
        # Extract the filter criteria from the request body
        filters = request.json
        # Ensure the series_id is an integer
        series_id = int(request.args.get('seriesId', 1))

        series = Series.query.filter_by(id=series_id, status=1).first()
        if not series:
            return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        # Get the fields related to this series
        fields_query = db.session.query(Field).filter(
            Field.series_id == series_id)

        fields = {field.id: field for field in fields_query.all()}

        missing_field = __check_field_required(
            fields_query, filters, Field.is_filtered)

        if (len(missing_field) != 0):
            return make_response(jsonify({"code": 400,
                                          "msg": f"Missing required field: {missing_field}"}), 400)

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

        for index, filter_criteria in enumerate(filters):
            field_id = filter_criteria['fieldId']
            value = filter_criteria['value']
            operation = filter_criteria.get('operation', 'equals')
            like = filter_criteria.get('like', 0)

            # Check if field_id exists in fields
            if field_id not in fields:
                return make_response(jsonify({
                    "code": 400,
                    "msg": f"Invalid fieldId: {field_id}"
                }), 400)

            # Check if the value is of the correct data type
            field = fields[field_id]
            type_err = __check_field_type(field, value)
            if (len(type_err) != 0):
                return make_response(jsonify({
                    "code": 400,
                    "msg": type_err
                }), 400)

            field_name = f'field_id{index}'
            value_name = f'value{index}'

            parameters[field_name] = field_id

            # like binding
            if like and field.data_type.lower() == 'string':
                parameters[value_name] = f"{value}%"
            else:
                parameters[value_name] = value

            condition = __check_condition(
                field, operation, field_name, value_name, like)
            conditions.append(condition)

        sql_query += " AND ".join(conditions)
        sql_query += ")"

        # Execute the SQL query
        result = db.session.execute(text(sql_query), parameters).fetchall()

        # Paginate the results
        paginated_result = result[(page-1)*limit: page*limit]

        # Get ERP data
        erp_data = read_erp(filters[1]['value'])
        fields_data += erp_data

        # Format the output
        data = []

        for row in paginated_result:
            fields_data = []
            item_id, item_series_id, item_name = row
            fields_data += [
                {"key": str(field.id), "value": __get_field_value_by_type(
                    item_id, field)}
                for field in fields.values()
            ]
            data.append({
                'itemId': item_id,
                'name': item_name,
                'seriesId': item_series_id,
                'fields': fields_data
            })

        return make_response(jsonify({"code": 200, "msg": "Success", "data": data}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def update_multi(data):
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
            item = db.session.get(Item, item_id)

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
                field = db.session.get(Field, field_id)

                if not field:
                    return make_response(jsonify({'code': 404, 'msg': f'field_id:{field_id} not found'}), 404)

                # Check if the value is of the correct data type
                type_err = __check_field_type(field, value)
                if (len(type_err) != 0):
                    return make_response(jsonify({
                        "code": 400,
                        "msg": type_err
                    }), 400)

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

        # 批次刪除 ItemAttribute 記錄
        db.session.query(ItemAttribute).filter(
            ItemAttribute.item_id.in_(item_ids)).delete(synchronize_session=False)

        # 批次刪除 Item 記錄
        db.session.query(Item).filter(Item.id.in_(item_ids)
                                      ).delete(synchronize_session=False)

        # 儲存變更到資料庫
        db.session.commit()

        # 回傳成功訊息
        return make_response(jsonify({'code': 200, 'msg': 'Items deleted'}), 200)

    except Exception as e:
        # 處理例外情況，回滾交易並回傳錯誤訊息
        db.session.rollback()
        return make_response(jsonify({'code': 500, 'msg': str(e)}), 500)

    finally:
        # 確保關閉資料庫連線
        db.session.close()


def __get_field_value_by_type(item_id, field):
    result = db.session.query(ItemAttribute).filter(
        and_(ItemAttribute.item_id == item_id,
             ItemAttribute.field_id == field.id)
    ).first()
    value = result.value
    data_type = result.field.data_type

    if (data_type == "number"):
        value = int(value)

    return value


def __check_field_required(fields_query, filters, is_required_var):
    missing_field = []

    # Check if all required fields are in the request body
    required_fields_query = fields_query.filter(is_required_var == True)
    required_fields = {
        field.id: field for field in required_fields_query.all()}
    for required_field_id in required_fields.keys():
        if not any(filter.get('fieldId') == required_field_id for filter in filters):
            missing_field.append(required_fields[required_field_id].name)
    return missing_field


def __is_datetime(string):
    try:
        datetime.strptime(string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def __check_field_type(field, value):
    type_err = []

    if field.data_type.lower() not in data_type_map:
        type_err.append(
            f"Incorrect data type for field: {field.name}. Expected {field.data_type.lower()}, got {type(value).__name__}.")

    # Check if the value is of the correct data type
    correct_type = data_type_map[field.data_type.lower()]
    if (correct_type == 'datetime'):
        if (not __is_datetime(value)):
            type_err.append(
                f"Incorrect data type for field: {field.name}. Expected {field.data_type.lower()}, got {type(value).__name__}.")

    else:
        if not isinstance(value, correct_type):
            type_err.append(
                f"Incorrect data type for field: {field.name}. Expected {field.data_type.lower()}, got {type(value).__name__}.")

    return type_err


def __check_condition(field, operation, field_name, value_name, like=0):
    condition = f"""
    (item.id, item.series_id, item.name) IN (
        SELECT DISTINCT item.id,
                        item.series_id,
                        item.name
        FROM item
            JOIN item_attribute ON item.id = item_attribute.item_id
        WHERE item.series_id = :series_id
            AND item_attribute.field_id = :{field_name}
            AND item_attribute.value = :{value_name}
    )
    """

    if operation == 'greater':
        if field.data_type.lower() == 'number':
            condition = f"""
            (item.id, item.series_id, item.name) IN (
                SELECT DISTINCT item.id,
                                item.series_id,
                                item.name
                FROM item
                    JOIN item_attribute ON item.id = item_attribute.item_id
                WHERE item.series_id = :series_id
                    AND item_attribute.field_id = :{field_name}
                    AND CAST(item_attribute.value AS float) >= :{value_name}
            )
            """
        elif field.data_type.lower() == 'datetime':
            condition = f"""
            (item.id, item.series_id, item.name) IN (
                SELECT DISTINCT item.id,
                                item.series_id,
                                item.name
                FROM item
                    JOIN item_attribute ON item.id = item_attribute.item_id
                WHERE item.series_id = :series_id
                    AND item_attribute.field_id = :{field_name}
                    AND CAST(item_attribute.value AS DATETIME) >= :{value_name}
            )
            """

    elif operation == 'less':
        if field.data_type.lower() == 'number':
            condition = f"""
            (item.id, item.series_id, item.name) IN (
                SELECT DISTINCT item.id,
                                item.series_id,
                                item.name
                FROM item
                    JOIN item_attribute ON item.id = item_attribute.item_id
                WHERE item.series_id = :series_id
                    AND item_attribute.field_id = :{field_name}
                    AND CAST(item_attribute.value AS float) <= :{value_name}
            )
            """
        elif field.data_type.lower() == 'datetime':
            condition = f"""
            (item.id, item.series_id, item.name) IN (
                SELECT DISTINCT item.id,
                                item.series_id,
                                item.name
                FROM item
                    JOIN item_attribute ON item.id = item_attribute.item_id
                WHERE item.series_id = :series_id
                    AND item_attribute.field_id = :{field_name}
                    AND CAST(item_attribute.value AS DATETIME) <= :{value_name}
            )
            """

    elif operation == 'equals':
        if field.data_type.lower() == 'string':
            if like:
                condition = f"""
                        (item.id, item.series_id, item.name) IN (
                            SELECT DISTINCT item.id,
                                            item.series_id,
                                            item.name
                            FROM item
                                JOIN item_attribute ON item.id = item_attribute.item_id
                            WHERE item.series_id = :series_id
                                AND item_attribute.field_id = :{field_name}
                                AND item_attribute.value LIKE :{value_name}
                        )
                        """
    return condition
