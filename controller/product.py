import os
from flask import current_app, jsonify, make_response, request
from controller.erp import read as read_erp
from models.series import Series, Field, Item, ItemAttribute
from models.user import User
from models.archive import Archive
from models.shared import db
from models.mapping_table import data_type_map
from models.image import Image
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, text
from datetime import datetime
import base64
from flask_jwt_extended import get_jwt_identity, get_jwt


def read(product_id):
    try:
        # Check if product_id is provided
        if not product_id:
            return make_response(jsonify({"code": 400, "msg": "Product ID is required"}), 400)

        # Get the item related to this product_id
        item = Item.query.get(product_id)

        # Check if product exists
        if not item:
            return make_response(jsonify({"code": 404, "msg": "Product not found"}), 404)

        # Check if the item is archived
        is_archived = Archive.query.filter_by(item_id=product_id).first()

        # Get the attributes related to this product
        attributes_query = db.session.query(ItemAttribute).filter(
            ItemAttribute.item_id == product_id)

        attributes = []
        erp_product_nos = set()  # Collect all ERP product numbers

        for attribute in attributes_query.all():
            attributes += [{"fieldId": attribute.field_id,
                            "fieldName": attribute.field.name,
                            "dataType": attribute.field.data_type,
                            "value": __get_field_value_by_type(attribute)}]

            # Collect erp product numbers
            if attribute.field.is_erp:
                erp_product_no = __get_field_value_by_type(attribute)
                if erp_product_no:
                    erp_product_nos.add(erp_product_no)

        # Fetch ERP data in bulk
        erp_data_map = read_erp(erp_product_nos)

        # Extract ERP data
        erp_data = []
        for product_no in erp_product_nos:
            erp_data += erp_data_map.get(product_no, [])

        # Format the output
        result = {
            "itemId": item.id,
            "seriesId": item.series_id,
            "attributes": attributes,
            "seriesName": item.series.name,
            "erp": erp_data,
            "hasArchive": bool(is_archived),
        }
        response = make_response(
            jsonify({"code": 200, "msg": "Success", "data": result}), 200)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

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
            attributes = item_data.get('attributes')

            # Get the fields related to this series
            fields_query = db.session.query(Field).filter(
                Field.series_id == series_id)

            if not series_id:
                return make_response(jsonify({"code": 400, "msg": "Incomplete data"}), 400)

            series = Series.query.get(series_id)

            if not series:
                return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

            item = Item(series_id=series_id)
            db.session.add(item)

            missing_field = __check_field_required(
                fields_query, attributes, Field.is_required)

            if len(missing_field) != 0:
                return make_response(jsonify({"code": 400, "msg": f"Missing required field: {missing_field}"}), 400)

            for field in fields_query:
                attribute = next(
                    (a for a in attributes if a.get('fieldId') == field.id), None)
                value = attribute.get('value') if attribute else None

                if field.data_type.lower() == 'picture' and value:
                    value = __save_image(value, item.id, field.id)

                item_attribute = ItemAttribute(
                    item_id=item.id, field_id=field.id, value=value)
                db.session.add(item_attribute)

            items.append(item)

        db.session.commit()

        result = [{'id': item.id, 'seriesId': item.series_id}
                  for item in items]
        return make_response(jsonify({"code": 201, "msg": "Success", "data": result}), 201)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read_multi(data):
    try:
        # Ensure the series_id is an integer
        series_id = data.get('seriesId')
        if not series_id:
            return make_response(jsonify({"code": 404, "msg": "SeriesId not found"}), 404)

        series = Series.query.filter_by(id=series_id, status=1).first()
        if not series:
            return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        sort_param = request.args.get('sort', None)
        sort_field_id, sort_order = None, None
        if sort_param:
            sort_parts = sort_param.split(',')
            if len(sort_parts) == 2:
                sort_field_id, sort_order = int(
                    sort_parts[0]), sort_parts[1].lower()
            else:
                return make_response(jsonify({"code": 400, "msg": "Invalid sort parameter"}), 400)

        # Extract the filter criteria from the request body
        filters = data.get('filters', [])

        # Get the fields related to this series
        fields_query = db.session.query(Field).filter(
            Field.series_id == series_id)

        fields = {field.id: field for field in fields_query.all()}

        # Create a SQL query to find the items
        sql_query = """
            SELECT item.id AS item_id,
                item.series_id AS item_series_id,
                s.name AS series_name
            FROM item
            JOIN series AS s ON item.series_id = s.id
            WHERE item.series_id = :series_id
        """

        conditions = []
        parameters = {'series_id': series_id}

        # if there is condition
        if len(filters) > 0:
            sql_query += """
                AND (
            """

            for index, filter_criteria in enumerate(filters):
                field_id = filter_criteria['fieldId']
                value = filter_criteria['value']
                operation = filter_criteria.get('operation', 'equals')

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
                if field.data_type.lower() == 'string':
                    parameters[value_name] = f"%{value}%"
                else:
                    parameters[value_name] = value

                condition = __check_condition(
                    field, operation, field_name, value_name)

                conditions.append(condition)

            sql_query += " AND ".join(conditions)
            sql_query += ")"

        if sort_field_id:
            sql_query += f" ORDER BY (SELECT value FROM item_attribute WHERE item_id = item.id AND field_id = :sort_field_id)"
            if sort_order == 'desc':
                sql_query += " DESC"
            parameters['sort_field_id'] = sort_field_id

        sql_query += " LIMIT :limit OFFSET :page"
        parameters["limit"] = limit
        parameters["page"] = (page - 1) * limit

        # Execute the SQL query
        result = db.session.execute(text(sql_query), parameters).fetchall()

        # Extract all product numbers from the result that need ERP data
        product_nos_to_fetch = set()
        for row in result:
            item_id, item_series_id, series_name = row
            for field in fields.values():
                if field.is_erp:
                    item = db.session.query(ItemAttribute).filter(
                        and_(ItemAttribute.item_id == item_id,
                             ItemAttribute.field_id == field.id)
                    ).first()
                    erp_product_no = __get_field_value_by_type(item)
                    product_nos_to_fetch.add(erp_product_no)

        # Fetch ERP data in a single call
        erp_data_map = read_erp(product_nos_to_fetch)

        # Format the output
        data = []

        # Get all relevant ItemAttributes in a single query
        item_ids = [row[0] for row in result]
        all_attributes = db.session.query(ItemAttribute).filter(
            and_(ItemAttribute.item_id.in_(item_ids))
        ).all()

        # Convert the list of attributes into a dictionary for easier look-up
        attributes_dict = {(attr.item_id, attr.field_id)
                            : attr for attr in all_attributes}

        for row in result:
            fields_data = []
            item_id, item_series_id, series_name = row
            erp_data = []
            for field in sorted(fields.values(), key=lambda x: x.sequence):
                item = attributes_dict.get((item_id, field.id))
                value = __get_field_value_by_type(item)
                # check permission disable field
                is_limit_permission_ok = True
                if field.is_limit_field:
                    is_limit_permission_ok = __check_field_permission(
                        'limit-field.read')
                if is_limit_permission_ok:
                    fields_data.append({
                        "fieldId": str(field.id),
                        "fieldName": field.name,
                        "dataType": field.data_type,
                        "value": value,
                    })

                # Get erp data
                if field.is_erp and value in erp_data_map:
                    erp_data += erp_data_map[value]

            data.append({
                'itemId': item_id,
                'seriesId': item_series_id,
                'seriesName': series_name,
                'attributes': fields_data,
                'erp': erp_data
            })

        # find archive exist
        item_ids = [item_data['itemId'] for item_data in data]

        archive_records = db.session.query(Archive.item_id).filter(
            Archive.item_id.in_(item_ids)).all()

        archive_item_ids = set(record[0] for record in archive_records)

        for item_data in data:
            item_id = item_data['itemId']
            item_data['hasArchive'] = item_id in archive_item_ids

        count_query = """
            SELECT COUNT(item.id) 
            FROM item
            JOIN series AS s ON item.series_id = s.id
            WHERE item.series_id = :series_id
        """
        # if there is condition
        if len(filters) > 0:
            count_query += __create_count_query(count_query, conditions)

        # Execute the count query
        count_result = db.session.execute(
            text(count_query), parameters).fetchone()
        total_count = count_result[0]

        # check archive.update permission not exist delete item with archive false
        is_archive_permission_ok = __check_field_permission("archive.create")

        if not is_archive_permission_ok:
            # archive.update not exist
            removed_count = 0  # record remove count

            for item_data in data.copy():
                item_id = item_data['itemId']
                has_archive = item_id in archive_item_ids

                if has_archive:
                    # if 'hasArchive' True，delete from data
                    data.remove(item_data)
                    removed_count += 1

            # 从 total_count 中减去被删除的数量
            total_count -= removed_count

        response = make_response(jsonify(
            {"code": 200, "msg": "Success", "data": data, "totalCount": total_count}), 200)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

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

        # 遍歷每個輸入項目
        for item_data in data:
            item_id = item_data.get('itemId')
            attributes = item_data.get('attributes')

            # 檢查輸入項目的完整性
            if not item_id or not attributes:
                return make_response(jsonify({'code': 400, 'msg': 'Incomplete data'}), 400)

            # 查詢對應的 Item 記錄
            item = Item.query.get(item_id)

            # 檢查 Item 是否存在
            if not item:
                return make_response(jsonify({'code': 404, 'msg': 'Item not found'}), 404)

            # 遍歷每個屬性
            for attribute in attributes:
                field_id = attribute.get('fieldId')
                value = attribute.get('value')

                # 檢查屬性的完整性
                if not field_id:
                    return make_response(jsonify({'code': 400, 'msg': 'Incomplete attribute data'}), 400)

                # 查詢對應的 Field 記錄
                field = Field.query.get(field_id)

                if not field:
                    return make_response(jsonify({'code': 404, 'msg': f'field_id:{field_id} not found'}), 404)

                # Check if the value is of the correct data type
                type_err = __check_field_type(field, value)
                if (len(type_err) != 0):
                    return make_response(jsonify({
                        "code": 400,
                        "msg": type_err
                    }), 400)

                item_attribute = db.session.query(ItemAttribute).filter_by(
                    item_id=item_id, field_id=field_id).first()

                if isinstance(value, bool):
                    value = 1 if value else 0

                if field.data_type.lower() == 'picture' and value:
                    value = __save_image(
                        value, item.id, field.id, item_attribute.value)

                if item_attribute:
                    item_attribute.value = value

        # 儲存變更到資料庫
        db.session.commit()

        # 回傳成功訊息
        return make_response(jsonify({'code': 200, 'msg': 'ItemAttributes updated'}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({'code': 500, 'msg': str(e)}), 500)

    finally:
        # 確保關閉資料庫連線
        db.session.close()


def delete(data):
    try:
        if not data or 'itemId' not in data:
            return make_response(jsonify({'code': 400, 'msg': 'Invalid data'}), 400)

        item_ids = data['itemId']

        items_to_delete = db.session.query(
            Item).filter(Item.id.in_(item_ids)).all()

        for item in items_to_delete:
            # Check if the item exists in the 'archive' table
            archive_item = db.session.query(
                Archive).filter_by(item_id=item.id).first()

            # If it exists in the 'archive' table, delete it
            if archive_item:
                db.session.delete(archive_item)

            for attribute in item.attributes:
                if attribute.field.data_type == 'picture':
                    image_id = attribute.value
                    image_to_delete = db.session.query(Image).get(image_id)
                    if image_to_delete:
                        if os.path.exists(image_to_delete.path):
                            os.remove(image_to_delete.path)

                        db.session.delete(image_to_delete)

            db.session.query(ItemAttribute).filter(
                ItemAttribute.item_id == item.id).delete(synchronize_session=False)

        db.session.query(Item).filter(Item.id.in_(item_ids)
                                      ).delete(synchronize_session=False)

        db.session.commit()

        return make_response(jsonify({'code': 200, 'msg': 'Items deleted'}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({'code': 500, 'msg': str(e)}), 500)

    finally:
        db.session.close()


def __save_image(image_data, item_id, field_id, image_id=None):
    # Extract base64 encoded image data
    if ',' in image_data:
        _, base64_data = image_data.split(',', 1)
    else:
        base64_data = image_data

    # Decode base64 data
    image_bytes = base64.b64decode(base64_data)

    # Check if the image is PNG or JPEG
    image_type = check_image_type(image_bytes)
    if image_type not in ['png', 'jpeg']:
        raise Exception("Only png or jpeg images are allowed.")

    # Define the directory to store the images
    image_dir = current_app.config['IMG_PATH']
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    # Define the image path
    image_name = f"image_{item_id}_{field_id}.png"
    image_path = os.path.join(image_dir, image_name)

    # Save the image to the file
    with open(image_path, 'wb') as image_file:
        image_file.write(image_bytes)

    if image_id:
        # If image_id exists, update the existing image path
        image = Image.query.get(image_id)
        if image:
            image.path = image_path  # store the path instead of the data
            db.session.commit()
        else:
            # Handle the case where the image_id doesn't exist
            raise Exception(
                "Image with the specified image_id does not exist.")
    else:
        # Save the image path as a new record in the Image table
        # store the path instead of the data
        image = Image(name=image_name[:-4], path=image_path)
        db.session.add(image)
        db.session.flush()

    return image.id


def check_image_type(image_bytes):
    # PNG files start with \x89PNG
    if image_bytes[:4] == b'\x89PNG':
        return 'png'
    # JPEG files start with \xFF\xD8
    elif image_bytes[:2] == b'\xFF\xD8':
        return 'jpeg'
    else:
        return 'unknown'


def __get_field_value_by_type(item):
    if not item or not item.value:
        return None

    value = item.value
    data_type = item.field.data_type

    if (data_type == "number"):
        value = float(value)
    elif (data_type == "boolean"):
        value = bool(int(value))
    elif (data_type == "picture"):
        # Get the corresponding image URL based on the image ID (value)
        value = f"/image/{value}"

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

    if value:
        if field.data_type.lower() not in data_type_map:
            type_err.append(
                f"Incorrect data type for field: {field.name}. Expected {field.data_type.lower()}, got {type(value).__name__}.")

        # Check if the value is of the correct data type
        correct_type = data_type_map[field.data_type.lower()]

        if correct_type == 'picture':
            # Check if the value is a valid base64-encoded string
            try:
                # This will raise an exception if the value is not a valid base64 string
                base64.b64decode(value)
            except base64.binascii.Error:
                type_err.append(
                    f"Incorrect data type for field: {field.name}. Expected {field.data_type.lower()}, got {type(value).__name__}."
                )

        elif (correct_type == 'datetime'):
            if (not __is_datetime(value)):
                type_err.append(
                    f"Incorrect data type for field: {field.name}. Expected {field.data_type.lower()}, got {type(value).__name__}.")

        else:
            if not isinstance(value, correct_type):
                type_err.append(
                    f"Incorrect data type for field: {field.name}. Expected {field.data_type.lower()}, got {type(value).__name__}.")

    return type_err


def __check_condition(field, operation, field_name, value_name):
    condition = f"""
    (item.id, item.series_id) IN (
        SELECT DISTINCT item.id,
                        item.series_id
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
            (item.id, item.series_id) IN (
                SELECT DISTINCT item.id,
                                item.series_id
                FROM item
                    JOIN item_attribute ON item.id = item_attribute.item_id
                WHERE item.series_id = :series_id
                    AND item_attribute.field_id = :{field_name}
                    AND CAST(item_attribute.value AS float) >= :{value_name}
            )
            """
        elif field.data_type.lower() == 'datetime':
            condition = f"""
            (item.id, item.series_id) IN (
                SELECT DISTINCT item.id,
                                item.series_id
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
            (item.id, item.series_id) IN (
                SELECT DISTINCT item.id,
                                item.series_id
                FROM item
                    JOIN item_attribute ON item.id = item_attribute.item_id
                WHERE item.series_id = :series_id
                    AND item_attribute.field_id = :{field_name}
                    AND CAST(item_attribute.value AS float) <= :{value_name}
            )
            """
        elif field.data_type.lower() == 'datetime':
            condition = f"""
            (item.id, item.series_id) IN (
                SELECT DISTINCT item.id,
                                item.series_id
                FROM item
                    JOIN item_attribute ON item.id = item_attribute.item_id
                WHERE item.series_id = :series_id
                    AND item_attribute.field_id = :{field_name}
                    AND CAST(item_attribute.value AS DATETIME) <= :{value_name}
            )
            """

    if field.data_type.lower() == 'string':
        condition = f"""
                (item.id, item.series_id) IN (
                    SELECT DISTINCT item.id,
                                    item.series_id
                    FROM item
                        JOIN item_attribute ON item.id = item_attribute.item_id
                    WHERE item.series_id = :series_id
                        AND item_attribute.field_id = :{field_name}
                        AND item_attribute.value LIKE :{value_name}
                )
                """
    return condition


def __check_field_permission(permission):
    user_id = get_jwt_identity()

    user = User.query.get(user_id)

    if user and has_permission(permission):
        return True
    return False


def __create_count_query(count_query, conditions):
    count_query += """
            AND (
        """
    # Using the same conditions for the count query
    count_query += " AND ".join(conditions)
    count_query += ")"

    return count_query


def has_permission(required_permission):
    permissions = get_jwt().get("permissions", [])
    if required_permission in permissions:
        return True
    return False
