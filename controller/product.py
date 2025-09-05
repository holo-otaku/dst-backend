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
from utils.permissions import check_field_permission, has_permission
from sqlalchemy import and_, text
from datetime import datetime
import base64
from flask_jwt_extended import get_jwt_identity, get_jwt
from modules.exception import handle_exceptions
from PIL import Image as PILImage
import io
import xlsxwriter
from io import BytesIO
from flask import send_file


@handle_exceptions
def read(product_id):
    # Check if product_id is provided
    if not product_id:
        return make_response(
            jsonify({"code": 400, "msg": "Product ID is required"}), 400
        )

    # Get the item related to this product_id
    item = db.session.get(Item, product_id)

    # Check if product exists
    if not item:
        return make_response(jsonify({"code": 404, "msg": "Product not found"}), 404)

    # Check if the item is archived
    is_archived = db.session.query(Archive).filter_by(item_id=product_id).first()

    # Get all fields for this series
    series_fields = db.session.query(Field).filter(
        Field.series_id == item.series_id
    ).order_by(Field.sequence).all()

    # Get the attributes related to this product
    attributes_query = db.session.query(ItemAttribute).filter(
        ItemAttribute.item_id == product_id
    )
    
    # Create a dictionary for quick lookup of existing attributes
    existing_attributes = {attr.field_id: attr for attr in attributes_query.all()}

    attributes = []
    erp_product_nos = set()  # Collect all ERP product numbers

    # Process all fields, including those without values in ItemAttribute
    for field in series_fields:
        attribute = existing_attributes.get(field.id)
        
        # Check permission for limited fields
        is_limit_permission_ok = True
        if field.is_limit_field:
            is_limit_permission_ok = check_field_permission("limit-field.read")
        
        if is_limit_permission_ok:
            attributes.append({
                "fieldId": field.id,
                "fieldName": field.name,
                "dataType": field.data_type,
                "value": __get_field_value_by_type(attribute) if attribute else None,
            })

            # Collect erp product numbers
            if field.search_erp and attribute:
                erp_product_no = __get_field_value_by_type(attribute)
                if erp_product_no:
                    erp_product_nos.add(erp_product_no)

    # Fetch ERP data in bulk
    erp_data_map = read_erp(erp_product_nos, item.series_id)

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
        "isDeleted": bool(item.is_deleted),
    }
    response = make_response(
        jsonify({"code": 200, "msg": "Success", "data": result}), 200
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@handle_exceptions
def create(data):
    items = []

    for item_data in data:
        series_id = item_data.get("seriesId")
        attributes = item_data.get("attributes")

        # Get the fields related to this series
        fields_query = db.session.query(Field).filter(Field.series_id == series_id)

        if not series_id:
            return make_response(jsonify({"code": 400, "msg": "Incomplete data"}), 400)

        series = db.session.get(Series, series_id)

        if not series:
            return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

        item = Item(series_id=series_id)
        db.session.add(item)

        missing_field = __check_field_required(
            fields_query, attributes, Field.is_required
        )

        if len(missing_field) != 0:
            return make_response(
                jsonify(
                    {"code": 400, "msg": f"Missing required field: {missing_field}"}
                ),
                400,
            )

        for field in fields_query:
            attribute = next(
                (a for a in attributes if a.get("fieldId") == field.id), None
            )
            value = attribute.get("value") if attribute else None

            # Check if the value is of the correct data type
            type_err = __check_field_type(field, value)
            if len(type_err) != 0:
                return make_response(jsonify({"code": 400, "msg": type_err}), 400)

            if field.data_type.lower() == "picture" and value:
                value = __save_image(value, item.id, field.id)

            item_attribute = ItemAttribute(
                item_id=item.id, field_id=field.id, value=value
            )
            db.session.add(item_attribute)

        items.append(item)

    db.session.commit()

    result = [{"id": item.id, "seriesId": item.series_id} for item in items]
    return make_response(jsonify({"code": 201, "msg": "Success", "data": result}), 201)


@handle_exceptions
def create_from_items(data):
    item_ids = data.get("itemIds", [])
    if not item_ids or not isinstance(item_ids, list):
        return make_response(
            jsonify({"code": 400, "msg": "itemIds must be a list"}), 400
        )

    new_items = []

    for item_id in item_ids:
        item = db.session.get(Item, item_id)
        if not item:
            return make_response(
                jsonify({"code": 404, "msg": f"Item {item_id} not found"}), 404
            )

        # 建立新 Item
        new_item = Item(series_id=item.series_id)
        db.session.add(new_item)
        db.session.flush()  # 取得 new_item.id

        # 複製對應的 attributes
        attributes = db.session.query(ItemAttribute).filter_by(item_id=item_id).all()
        # 按照欄位的 sequence 排序，確保按正確順序處理
        attributes_with_field = []
        for attr in attributes:
            field = db.session.get(Field, attr.field_id)
            attributes_with_field.append((attr, field))
        
        # 按照 field.sequence 排序
        attributes_with_field.sort(key=lambda x: x[1].sequence if x[1].sequence is not None else float('inf'))
        
        first_string_field_modified = False  # 每個 item 都重設標記
        
        for attr, field in attributes_with_field:
            new_value = attr.value
            # 如果是圖片類型，需要另外處理圖片複製
            if field.data_type == "picture" and attr.value:
                new_value = __copy_image(attr.value, new_item.id, attr.field_id)
            # 如果是第一個遇到的字串類型欄位，加上 "copy" 前綴
            elif field.data_type == "string" and attr.value and not first_string_field_modified:
                new_value = f"copy {attr.value}"
                first_string_field_modified = True

            new_attr = ItemAttribute(
                item_id=new_item.id, field_id=attr.field_id, value=new_value
            )
            db.session.add(new_attr)

        new_items.append(new_item)

    db.session.commit()
    result = [{"id": item.id, "seriesId": item.series_id} for item in new_items]
    return make_response(jsonify({"code": 201, "msg": "Success", "data": result}), 201)


@handle_exceptions
def read_multi(data):
    try:
        data, total_count, _ = __get_series_data(data, for_export=False)
        return make_response(
            jsonify(
                {"code": 200, "msg": "Success", "data": data, "totalCount": total_count}
            ),
            200,
        )
    except ValueError as e:
        return make_response(jsonify({"code": 400, "msg": str(e)}), 400)


@handle_exceptions
def export_excel(data):
    try:
        rows, _, _ = __get_series_data(data, for_export=True)

        if not rows:
            return make_response(
                jsonify({"code": 204, "msg": "No data to export"}), 200
            )

        # 取得欄位名稱（以第一筆 attributes 為基準）
        field_names = [attr["fieldName"] for attr in rows[0]["attributes"]]
        
        # 取得 ERP 欄位名稱（如果有的話）
        erp_field_names = []
        if rows[0].get("erp"):
            erp_field_names = [erp_field["key"] for erp_field in rows[0]["erp"]]
        
        # 合併所有欄位名稱
        all_field_names = field_names + erp_field_names

        # 建立 Excel 檔案在記憶體中
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Products")

        # 寫入表頭
        for col, name in enumerate(all_field_names):
            worksheet.write(0, col, name)

        # 寫入每列資料
        for row_idx, row in enumerate(rows, start=1):
            col_idx = 0
            
            # 寫入一般欄位資料
            attr_list = row.get("attributes", [])
            for attr in attr_list:
                value = attr.get("value", "")
                worksheet.write(row_idx, col_idx, value)
                col_idx += 1
            
            # 寫入 ERP 欄位資料
            erp_list = row.get("erp", [])
            for erp_field in erp_list:
                value = erp_field.get("value", "")
                worksheet.write(row_idx, col_idx, value)
                col_idx += 1

        workbook.close()
        output.seek(0)

        # 使用 UTC+8 時間生成檔名
        from datetime import datetime, timezone, timedelta
        utc_plus_8 = timezone(timedelta(hours=8))
        current_time = datetime.now(utc_plus_8)
        timestamp = current_time.strftime("%Y%m%d_%H%M%S")
        filename = f"products_export_{timestamp}.xlsx"

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )

    except ValueError as e:
        return make_response(jsonify({"code": 400, "msg": str(e)}), 400)


@handle_exceptions
def update_multi(data):
    # 檢查輸入資料的完整性
    if not data:
        return make_response(jsonify({"code": 400, "msg": "Empty data"}), 400)

    # 遍歷每個輸入項目
    for item_data in data:
        item_id = item_data.get("itemId")
        is_deleted = item_data.get("isDeleted")
        attributes = item_data.get("attributes", [])

        # 檢查輸入項目的完整性
        if not item_id:
            return make_response(jsonify({"code": 400, "msg": "Incomplete data"}), 400)

        # 查詢對應的 Item 記錄
        item = db.session.get(Item, item_id)

        # 檢查 Item 是否存在
        if not item:
            return make_response(jsonify({"code": 404, "msg": "Item not found"}), 404)

        if is_deleted in [0, 1]:
            item.is_deleted = is_deleted

        item.updated_at = datetime.now()

        # 遍歷每個屬性
        for attribute in attributes:
            field_id = attribute.get("fieldId")
            value = attribute.get("value")

            # 檢查屬性的完整性
            if not field_id:
                return make_response(
                    jsonify({"code": 400, "msg": "Incomplete attribute data"}), 400
                )

            # 查詢對應的 Field 記錄
            field = db.session.get(Field, field_id)
            if not field:
                return make_response(
                    jsonify({"code": 404, "msg": f"field_id:{field_id} not found"}), 404
                )

            # Check if the value is of the correct data type
            type_err = __check_field_type(field, value)
            if len(type_err) != 0:
                return make_response(jsonify({"code": 400, "msg": type_err}), 400)

            item_attribute = (
                db.session.query(ItemAttribute)
                .filter_by(item_id=item_id, field_id=field_id)
                .first()
            )

            if isinstance(value, bool):
                value = 1 if value else 0

            if field.data_type.lower() == "picture":
                if value:
                    value = __save_image(value, item.id, field.id, item_attribute.value)
                else:
                    if item_attribute.value:
                        __delete_image(item_attribute.value)

            if item_attribute:
                item_attribute.value = value

    # 儲存變更到資料庫
    db.session.commit()

    # 回傳成功訊息
    return make_response(jsonify({"code": 200, "msg": "ItemAttributes updated"}), 200)


@handle_exceptions
def delete(data):
    if not data or "itemId" not in data:
        return make_response(jsonify({"code": 400, "msg": "Invalid data"}), 400)

    item_ids = data["itemId"]

    items_to_delete = db.session.query(Item).filter(Item.id.in_(item_ids)).all()

    for item in items_to_delete:
        item.is_deleted = 1

    db.session.commit()

    return make_response(jsonify({"code": 200, "msg": "Items deleted"}), 200)


def __get_series_data(data, for_export=False):
    """
    共用產品查詢邏輯，可用於一般查詢或 Excel 匯出
    - data: dict，包含 seriesId, filters
    - for_export: True 表示匯出（不限制筆數），False 表示有分頁限制
    """
    series_id = data.get("seriesId")
    if not series_id:
        raise ValueError("SeriesId not found")

    is_deleted = data.get("isDeleted", 0)
    if is_deleted not in [0, 1]:
        raise ValueError("Input body error")

    is_archived = data.get("isArchived")
    if is_archived is not None and is_archived not in [0, 1]:
        raise ValueError("isArchived must be 0 or 1")

    series = db.session.query(Series).filter_by(id=series_id, status=1).first()
    if not series:
        raise ValueError("Series not found")

    page = int(request.args.get("page", 1)) if not for_export else 1
    limit = int(request.args.get("limit", 10)) if not for_export else 999999
    sort_param = request.args.get("sort", None)

    sort_field_id, sort_order = None, None
    if sort_param:
        sort_parts = sort_param.split(",")
        if len(sort_parts) == 2:
            sort_field_id, sort_order = int(sort_parts[0]), sort_parts[1].lower()
        else:
            raise ValueError("Invalid sort parameter")

    filters = data.get("filters", [])

    # 取得欄位資訊
    fields = {
        field.id: field
        for field in db.session.query(Field).filter(Field.series_id == series_id)
    }

    # 驗證欄位與資料型別
    for filter_criteria in filters:
        field_id = filter_criteria["fieldId"]
        if field_id not in fields:
            raise ValueError(f"Invalid fieldId: {field_id}")
        value = filter_criteria["value"]
        type_err = __check_field_type(fields[field_id], value)
        if len(type_err) != 0:
            raise ValueError(type_err)

    # 查詢資料
    items, conditions, parameters = __get_items(
        series_id,
        filters,
        fields,
        sort_field_id,
        sort_order,
        limit,
        page,
        is_deleted,
        is_archived,
    )
    erp_data_map = __read_erp(items, fields, series_id)
    data = __combine_data_result(items, fields, erp_data_map)
    total_count = __count_total_count(
        data, filters, conditions, parameters, is_deleted, is_archived
    )

    return data, total_count, fields


def __save_image(image_data, item_id, field_id, image_id=None):
    # Extract base64 encoded image data
    if "," in image_data:
        _, base64_data = image_data.split(",", 1)
    else:
        base64_data = image_data

    image_name, image_path = __img_path_and_name(item_id, field_id)
    # image exist
    if base64_data and base64_data != "":
        # Decode base64 data
        image_bytes = base64.b64decode(base64_data)

        # Save the image to the file
        with open(image_path, "wb") as image_file:
            image_file.write(image_bytes)

    if image_id:
        # If image_id exists, update the existing image path
        image = db.session.get(Image, image_id)
        if image:
            image.path = image_path  # store the path instead of the data
            db.session.commit()
        else:
            # Handle the case where the image_id doesn't exist
            raise Exception("Image with the specified image_id does not exist.")
    else:
        # Save the image path as a new record in the Image table
        # store the path instead of the data
        image = Image(name=image_name[:-4], path=image_path)
        db.session.add(image)
        db.session.flush()

    return image.id


def __copy_image(source_image_id, new_item_id, field_id):
    """複製圖片檔案到新的位置，用於產品複製功能"""
    import os
    import shutil
    
    # 如果沒有圖片 ID，返回 None
    if not source_image_id:
        return None
    
    try:
        # 從資料庫中找到原始圖片記錄
        source_image = db.session.get(Image, source_image_id)
        if not source_image:
            current_app.logger.warning(f"Source image not found in database: {source_image_id}")
            return None
        
        # 檢查原始圖片檔案是否存在
        if not os.path.exists(source_image.path):
            current_app.logger.warning(f"Source image file not found: {source_image.path}")
            return None
        
        # 產生新的圖片名稱和路徑
        new_image_name, new_image_path = __img_path_and_name(new_item_id, field_id)
        
        # 複製圖片檔案
        shutil.copy2(source_image.path, new_image_path)
        
        # 在資料庫中建立新的圖片記錄
        new_image = Image(name=new_image_name[:-4], path=new_image_path)
        db.session.add(new_image)
        db.session.flush()
        
        return new_image.id
        
    except Exception as e:
        current_app.logger.error(f"Error copying image: {str(e)}")
        return None


def __delete_image(image_id):
    image = db.session.get(Image, image_id)
    if image:
        image_path = image.path

        db.session.delete(image)

        if os.path.exists(image_path):
            os.remove(image_path)
    else:
        raise Exception("Image with the specified image_id does not exist.")


def __img_path_and_name(item_id, field_id):
    # Define the directory to store the images
    image_dir = current_app.config["IMG_PATH"]
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    # Define the image path
    image_name = f"image_{item_id}_{field_id}.png"
    image_path = os.path.join(image_dir, image_name)

    return image_name, image_path


def __get_field_value_by_type(item):
    if not item or not item.value:
        return None

    value = item.value
    data_type = item.field.data_type

    if data_type == "number":
        value = str(value)
    elif data_type == "boolean":
        value = bool(int(value))
    elif data_type == "picture":
        # Get the corresponding image URL based on the image ID (value)
        value = f"/image/{value}"

    return value


def __check_field_required(fields_query, filters, is_required_var):
    missing_field = []

    # Check if all required fields are in the request body
    required_fields_query = fields_query.filter(is_required_var == True)
    required_fields = {field.id: field for field in required_fields_query.all()}
    for required_field_id in required_fields.keys():
        if not any(filter.get("fieldId") == required_field_id for filter in filters):
            missing_field.append(required_fields[required_field_id].name)
    return missing_field


def __is_datetime(string):
    """
    檢查字串是否為有效的日期格式
    支援多種日期格式：
    - %Y/%m/%d (2025/01/07)
    - %m/%d/%y (01/07/25)
    - %m/%d/%Y (01/07/2025)
    - %Y-%m-%d (2025-01-07)
    - %d/%m/%Y (07/01/2025)
    """
    date_formats = [
        "%Y/%m/%d",  # 2025/01/07
        "%m/%d/%y",  # 01/07/25
        "%m/%d/%Y",  # 01/07/2025
        "%Y-%m-%d",  # 2025-01-07
        "%d/%m/%Y",  # 07/01/2025
        "%d-%m-%Y",  # 07-01-2025
    ]
    
    for date_format in date_formats:
        try:
            datetime.strptime(string, date_format)
            return True
        except ValueError:
            continue
    
    return False


def __normalize_date(date_string):
    """
    將不同格式的日期字串標準化為 YYYY-MM-DD 格式
    """
    if not date_string:
        return None
        
    date_formats = [
        "%Y/%m/%d",  # 2025/01/07
        "%m/%d/%y",  # 01/07/25
        "%m/%d/%Y",  # 01/07/2025
        "%Y-%m-%d",  # 2025-01-07
        "%d/%m/%Y",  # 07/01/2025
        "%d-%m-%Y",  # 07-01-2025
    ]
    
    for date_format in date_formats:
        try:
            parsed_date = datetime.strptime(date_string, date_format)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


def __check_field_type(field, value):
    type_err = []

    if value:
        if field.data_type.lower() not in data_type_map:
            type_err.append(
                f"Incorrect data type for field: {field.name}. Expected {field.data_type.lower()}, got {type(value).__name__}."
            )

        # Check if the value is of the correct data type
        data_type = field.data_type.lower()
        correct_type = data_type_map[data_type]

        if data_type == "picture":
            # Check if the value is a valid base64-encoded string
            encoded_data = value.split(",")[1]
            decoded_data = base64.b64decode(encoded_data)
            img = PILImage.open(io.BytesIO(decoded_data))
            if img.format is None or img.format.lower() not in ["jpeg", "jpg", "png"]:
                type_err.append(
                    f"Incorrect data type for field: {field.name}. Expected {data_type}, got {type(value).__name__}."
                )

        elif data_type == "datetime":
            if not __is_datetime(value):
                type_err.append(
                    f"Incorrect data type for field: {field.name}. Expected {data_type}, got {type(value).__name__}."
                )

        elif data_type == "number":
            try:
                value = float(value)
            except:
                type_err.append(
                    f"Incorrect data type for field: {field.name}. Expected {data_type}, got {type(value).__name__}."
                )

        elif data_type == "string":
            try:
                value = str(value)
            except:
                type_err.append(
                    f"Incorrect data type for field: {field.name}. Expected {data_type}, got {type(value).__name__}."
                )

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

    if operation == "greater":
        if field.data_type.lower() == "number":
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
        elif field.data_type.lower() == "datetime":
            condition = f"""
            (item.id, item.series_id) IN (
                SELECT DISTINCT item.id,
                                item.series_id
                FROM item
                    JOIN item_attribute ON item.id = item_attribute.item_id
                WHERE item.series_id = :series_id
                    AND item_attribute.field_id = :{field_name}
                    AND DATE(item_attribute.value) >= DATE(:{value_name})
            )
            """

    elif operation == "less":
        if field.data_type.lower() == "number":
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
        elif field.data_type.lower() == "datetime":
            condition = f"""
            (item.id, item.series_id) IN (
                SELECT DISTINCT item.id,
                                item.series_id
                FROM item
                    JOIN item_attribute ON item.id = item_attribute.item_id
                WHERE item.series_id = :series_id
                    AND item_attribute.field_id = :{field_name}
                    AND DATE(item_attribute.value) <= DATE(:{value_name})
            )
            """
    elif operation in ["equals", "equal"] and field.data_type.lower() == "datetime":
        # 對於日期相等比較，使用 DATE() 函數確保只比較日期部分
        condition = f"""
        (item.id, item.series_id) IN (
            SELECT DISTINCT item.id,
                            item.series_id
            FROM item
                JOIN item_attribute ON item.id = item_attribute.item_id
            WHERE item.series_id = :series_id
                AND item_attribute.field_id = :{field_name}
                AND DATE(item_attribute.value) = DATE(:{value_name})
        )
        """

    if field.data_type.lower() == "string":
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


def __create_count_query(count_query, conditions):
    count_query += """
            AND (
        """
    # Using the same conditions for the count query
    count_query += " AND ".join(conditions)
    count_query += ")"

    return count_query


def __get_items(
    series_id,
    filters,
    fields,
    sort_field_id,
    sort_order,
    limit,
    page,
    is_deleted=0,
    is_archived=None,
):
    # Create a SQL query to find the items
    sql_query = """
            SELECT item.id AS item_id,
                item.series_id AS item_series_id,
                s.name AS series_name
            FROM item
            JOIN series AS s ON item.series_id = s.id
            WHERE item.series_id = :series_id
            AND item.is_deleted = :is_deleted
        """

    conditions = []
    parameters = {"series_id": series_id, "is_deleted": is_deleted}

    if is_archived is not None:
        if is_archived == 1:
            sql_query += " AND item.id IN (SELECT item_id FROM archive)"
        else:
            sql_query += " AND item.id NOT IN (SELECT item_id FROM archive)"

    # if there is condition
    if len(filters) > 0:
        sql_query += """
                AND (
            """

        for index, filter_criteria in enumerate(filters):
            field_id = filter_criteria["fieldId"]
            value = filter_criteria["value"]
            operation = filter_criteria.get("operation", "equals")
            field = fields[field_id]

            field_name = f"field_id{index}"
            value_name = f"value{index}"

            parameters[field_name] = field_id

            # 處理不同資料型別的值綁定
            if field.data_type.lower() == "string":
                parameters[value_name] = f"%{value}%"
            elif field.data_type.lower() == "datetime":
                # 標準化日期格式為 YYYY-MM-DD
                normalized_date = __normalize_date(value)
                if normalized_date:
                    parameters[value_name] = normalized_date
                else:
                    # 如果日期格式無效，使用原始值（可能會導致查詢失敗，但會有適當的錯誤處理）
                    parameters[value_name] = value
            else:
                parameters[value_name] = value

            condition = __check_condition(field, operation, field_name, value_name)

            conditions.append(condition)

        sql_query += " AND ".join(conditions)
        sql_query += ")"

    if sort_field_id:
        sql_query += f" ORDER BY (SELECT value FROM item_attribute WHERE item_id = item.id AND field_id = :sort_field_id)"
        if sort_order == "desc":
            sql_query += " DESC"
        parameters["sort_field_id"] = sort_field_id

    sql_query += " LIMIT :limit OFFSET :page"
    parameters["limit"] = limit
    parameters["page"] = (page - 1) * limit

    # Execute the SQL query
    result = db.session.execute(text(sql_query), parameters).fetchall()

    return result, conditions, parameters


def __combine_data_result(items, fields, erp_data_map):
    # Format the output
    data = []

    # Get all relevant ItemAttributes in a single query
    item_ids = [row[0] for row in items]
    all_attributes = (
        db.session.query(ItemAttribute)
        .filter(and_(ItemAttribute.item_id.in_(item_ids)))
        .all()
    )

    # Convert the list of attributes into a dictionary for easier look-up
    attributes_dict = {(attr.item_id, attr.field_id): attr for attr in all_attributes}

    

    for row in items:
        fields_data = []
        item_id, item_series_id, series_name = row
        erp_data = []
        for field in sorted(fields.values(), key=lambda x: x.sequence):
            item = attributes_dict.get((item_id, field.id))
            value = __get_field_value_by_type(item)
            # check permission disable field
            is_limit_permission_ok = True
            if field.is_limit_field:
                is_limit_permission_ok = check_field_permission("limit-field.read")
            if is_limit_permission_ok and not field.is_erp:
                fields_data.append(
                    {
                        "fieldId": str(field.id),
                        "fieldName": field.name,
                        "dataType": field.data_type,
                        "value": value,
                    }
                )

            # Get erp data
            if field.search_erp and value in erp_data_map:
                erp_data += erp_data_map[value]

        data.append(
            {
                "itemId": item_id,
                "seriesId": item_series_id,
                "seriesName": series_name,
                "attributes": fields_data,
                "erp": erp_data,
            }
        )

    return data


def __count_total_count(
    data, filters, conditions, parameters, status_filter=1, is_archived=None
):
    # find archive exist
    item_ids = [item_data["itemId"] for item_data in data]

    archive_records = (
        db.session.query(Archive.item_id).filter(Archive.item_id.in_(item_ids)).all()
    )

    archive_item_ids = set(record[0] for record in archive_records)

    for item_data in data:
        item_id = item_data["itemId"]
        item_data["hasArchive"] = item_id in archive_item_ids

    count_query = """
            SELECT COUNT(item.id) 
            FROM item
            JOIN series AS s ON item.series_id = s.id
            WHERE item.series_id = :series_id
            AND item.is_deleted = :is_deleted
        """

    if is_archived is not None:
        if is_archived == 1:
            count_query += " AND item.id IN (SELECT item_id FROM archive)"
        else:
            count_query += " AND item.id NOT IN (SELECT item_id FROM archive)"

    # if there is condition
    if len(filters) > 0:
        count_query = __create_count_query(count_query, conditions)

    # Execute the count query
    count_result = db.session.execute(text(count_query), parameters).fetchone()
    total_count = count_result[0]

    # check archive.update permission not exist delete item with archive false
    is_archive_permission_ok = check_field_permission("archive.create")

    if not is_archive_permission_ok:
        # archive.update not exist
        removed_count = 0  # record remove count

        for item_data in data.copy():
            item_id = item_data["itemId"]
            has_archive = item_id in archive_item_ids

            if has_archive:
                # if 'hasArchive' True，delete from data
                data.remove(item_data)
                removed_count += 1

        # 从 total_count 中减去被删除的数量
        total_count -= removed_count

    return total_count


def __read_erp(items, fields, series_id):
    # Extract all product numbers from the result that need ERP data
    product_nos_to_fetch = set()
    for row in items:
        item_id, item_series_id, series_name = row
        for field in fields.values():
            if field.search_erp:
                item = (
                    db.session.query(ItemAttribute)
                    .filter(
                        and_(
                            ItemAttribute.item_id == item_id,
                            ItemAttribute.field_id == field.id,
                        )
                    )
                    .first()
                )
                erp_product_no = __get_field_value_by_type(item)
                product_nos_to_fetch.add(erp_product_no)

    # Fetch ERP data in a single call
    return read_erp(product_nos_to_fetch, series_id)
