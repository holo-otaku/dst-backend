import os
from flask import current_app, jsonify, make_response, request
from controller import field_value, product_query
from controller.erp import read as read_erp
from models.series import Series, Field, Item, ItemAttribute
from models.user import User
from models.archive import Archive
from models.shared import db
from models.image import Image
from sqlalchemy.exc import SQLAlchemyError
from utils.permissions import check_field_permission, has_permission
from sqlalchemy import and_
import base64
from flask_jwt_extended import get_jwt_identity, get_jwt
from modules.exception import handle_exceptions
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

    # Check if product exists (items of a deleted series count as not found)
    if not item or item.series.status == 0:
        return make_response(jsonify({"code": 404, "msg": "Product not found"}), 404)

    # Check if the item is archived
    is_archived = db.session.query(Archive).filter_by(item_id=product_id).first()

    # Archived items are hidden from users without archive permission, as in search
    if is_archived and not check_field_permission("archive.create"):
        return make_response(jsonify({"code": 404, "msg": "Product not found"}), 404)

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
                "value": field_value.present(field.data_type, attribute.value if attribute else None),
            })

            # Collect erp product numbers
            if field.search_erp and attribute:
                erp_product_no = field_value.present(field.data_type, attribute.value)
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
        payload = __normalize_payload_from_request(item_data)
        item, error_response = __create_item(payload, mode="create")
        if error_response:
            return error_response
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

    items_query = db.session.query(Item).filter(Item.id.in_(item_ids))
    # Archived items are hidden from users without archive permission, as in search
    if not check_field_permission("archive.create"):
        items_query = items_query.filter(~Item.id.in_(db.session.query(Archive.item_id)))
    items_by_id = items_query.all()
    found_ids = {item.id for item in items_by_id}
    missing_ids = [item_id for item_id in item_ids if item_id not in found_ids]
    if missing_ids:
        return make_response(
            jsonify({"code": 404, "msg": f"Item(s) not found: {missing_ids}"}),
            404,
        )

    for item in items_by_id:
        payload = __normalize_payload_from_item(item)
        item_created, error_response = __create_item(payload, mode="copy")
        if error_response:
            return error_response
        new_items.append(item_created)

    db.session.commit()
    result = [{"id": item.id, "seriesId": item.series_id} for item in new_items]
    return make_response(jsonify({"code": 201, "msg": "Success", "data": result}), 201)


@handle_exceptions
def read_multi(data):
    try:
        data, total_count, _ = product_query.search(
            data,
            page=int(request.args.get("page", 1)),
            limit=int(request.args.get("limit", 10)),
            sort=request.args.get("sort"),
        )
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
        rows, _, fields = product_query.search(data, sort=request.args.get("sort"))

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
        # Stored values are user input: write them as text, never as formulas or links
        workbook = xlsxwriter.Workbook(
            output, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False}
        )
        worksheet = workbook.add_worksheet("Products")

        # 凍結前面五個欄位
        worksheet.freeze_panes(1, 5)  # 從第1列（標題列之後）和第5欄開始凍結

        # 設定欄位寬度和列高度，特別是圖片欄位
        default_row_height = 20
        image_row_height = 80  # 圖片列的高度
        has_image_cols = []
        
        # 檢查哪些欄位是圖片類型
        for col_idx, attr in enumerate(rows[0]["attributes"]):
            field_id = int(attr["fieldId"])
            if field_id in fields and fields[field_id].data_type == "picture":
                has_image_cols.append(col_idx)
                worksheet.set_column(col_idx, col_idx, 15)  # 設定圖片欄位寬度

        # 寫入表頭
        for col, name in enumerate(all_field_names):
            worksheet.write(0, col, name)

        # 寫入每列資料
        for row_idx, row in enumerate(rows, start=1):
            # 如果這一行有圖片，設定行高
            has_image_in_row = False
            
            col_idx = 0
            
            # 寫入一般欄位資料
            attr_list = row.get("attributes", [])
            for attr_idx, attr in enumerate(attr_list):
                value = attr.get("value", "")
                data_type = attr.get("dataType", "")
                
                if data_type == "picture" and value:
                    # 處理圖片欄位
                    has_image_in_row = True
                    try:
                        image_id = field_value.image_id(value)
                        if image_id:
                            # 從資料庫獲取圖片路徑
                            image_record = db.session.get(Image, image_id)
                            if image_record and os.path.exists(image_record.path):
                                # 插入圖片到 Excel
                                worksheet.insert_image(row_idx, col_idx, image_record.path, {
                                    'x_scale': 0.3,  # 縮放比例
                                    'y_scale': 0.3,
                                    'x_offset': 2,   # 偏移
                                    'y_offset': 2
                                })
                            else:
                                worksheet.write(row_idx, col_idx, "圖片不存在")
                        else:
                            worksheet.write(row_idx, col_idx, value)
                    except Exception as e:
                        # 如果圖片處理失敗，寫入錯誤訊息
                        worksheet.write(row_idx, col_idx, f"圖片載入失敗: {str(e)}")
                else:
                    # 一般欄位
                    worksheet.write(row_idx, col_idx, value)
                col_idx += 1
            
            # 設定行高
            if has_image_in_row:
                worksheet.set_row(row_idx, image_row_height)
            else:
                worksheet.set_row(row_idx, default_row_height)
            
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
        if not item or item.series.status == 0:
            return make_response(jsonify({"code": 404, "msg": "Item not found"}), 404)

        if is_deleted in [0, 1]:
            # 刪除/還原和 DELETE /product/delete 一樣需要 product.delete
            if not has_permission("product.delete"):
                db.session.rollback()
                return make_response(jsonify({"code": 403, "msg": "Permission denied"}), 403)
            item.is_deleted = is_deleted

        # 檢查供應商料號和DST料號是否已經存在（排除當前項目）
        duplicate_fields = __check_duplicate_required_fields(
            item.series_id, attributes, exclude_item_id=item_id
        )
        if duplicate_fields:
            return make_response(
                jsonify({"code": 400, "msg": f"Duplicate values found: {duplicate_fields}"}),
                400,
            )

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
            type_err = field_value.check(field, value)
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


def __get_fields_by_series(series_id):
    return (
        db.session.query(Field)
        .filter(Field.series_id == series_id)
        .order_by(Field.sequence)
        .all()
    )


def __normalize_payload_from_request(item_data):
    return {
        "series_id": item_data.get("seriesId"),
        "attributes": item_data.get("attributes", []),
    }


def __normalize_payload_from_item(item):
    fields = __get_fields_by_series(item.series_id)
    attributes_query = db.session.query(ItemAttribute).filter_by(item_id=item.id)
    attributes_by_field = {attr.field_id: attr for attr in attributes_query.all()}

    normalized_attributes = []
    first_string_field_modified = False

    for field in fields:
        source_attr = attributes_by_field.get(field.id)
        value = source_attr.value if source_attr else None

        if field.data_type == "picture" and value:
            normalized_attributes.append({"fieldId": field.id, "value": value})
        elif field.data_type == "string" and value and not first_string_field_modified:
            normalized_attributes.append({"fieldId": field.id, "value": f"copy {value}"})
            first_string_field_modified = True
        else:
            normalized_attributes.append({"fieldId": field.id, "value": value})

    return {
        "series_id": item.series_id,
        "attributes": normalized_attributes,
        "fields": fields,
    }


def __create_item(payload, mode="create"):
    series_id = payload.get("series_id")
    attributes = payload.get("attributes", [])
    fields = payload.get("fields")

    if not series_id:
        return None, make_response(
            jsonify({"code": 400, "msg": "Incomplete data"}), 400
        )

    series = db.session.get(Series, series_id)
    if not series or series.status == 0:
        return None, make_response(
            jsonify({"code": 404, "msg": "Series not found"}), 404
        )

    fields_query = db.session.query(Field).filter(Field.series_id == series_id)
    if fields is None:
        fields = fields_query.order_by(Field.sequence).all()

    missing_field = __check_field_required(fields_query, attributes, Field.is_required)
    if len(missing_field) != 0:
        return None, make_response(
            jsonify({"code": 400, "msg": f"Missing required field: {missing_field}"}),
            400,
        )

    if mode != "copy":
        duplicate_fields = __check_duplicate_required_fields(series_id, attributes)
        if duplicate_fields:
            return None, make_response(
                jsonify({"code": 400, "msg": f"Duplicate values found: {duplicate_fields}"}),
                400,
            )

    item = Item(series_id=series_id)
    db.session.add(item)
    db.session.flush()

    for field in fields:
        attribute = next(
            (a for a in attributes if a.get("fieldId") == field.id), None
        )
        value = attribute.get("value") if attribute else None

        # Only run type checking for create mode to avoid base64 expectations on copy
        if mode != "copy":
            type_err = field_value.check(field, value)
            if len(type_err) != 0:
                return None, make_response(jsonify({"code": 400, "msg": type_err}), 400)

        if field.data_type.lower() == "picture" and value:
            if mode == "copy":
                value = __copy_image(value, item.id, field.id)
            else:
                value = __save_image(value, item.id, field.id)

        item_attribute = ItemAttribute(item_id=item.id, field_id=field.id, value=value)
        db.session.add(item_attribute)

    return item, None


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


def __check_field_required(fields_query, filters, is_required_var):
    missing_field = []

    # Check if all required fields are in the request body
    required_fields_query = fields_query.filter(is_required_var == True)
    required_fields = {field.id: field for field in required_fields_query.all()}
    for required_field_id in required_fields.keys():
        if not any(filter.get("fieldId") == required_field_id for filter in filters):
            missing_field.append(required_fields[required_field_id].name)
    return missing_field


def __check_duplicate_required_fields(series_id, attributes, exclude_item_id=None):
    """檢查供應商料號和DST料號是否已經存在，可選擇排除指定 item。"""
    duplicate_fields = []

    supplier_field = db.session.query(Field).filter(
        and_(Field.series_id == series_id, Field.name == "供應商料號")
    ).first()

    dst_field = db.session.query(Field).filter(
        and_(Field.series_id == series_id, Field.name == "DST料號")
    ).first()

    base_filters = [Item.series_id == series_id, Item.is_deleted == 0]
    if exclude_item_id is not None:
        base_filters.append(Item.id != exclude_item_id)

    if supplier_field:
        supplier_attr = next(
            (a for a in attributes if a.get("fieldId") == supplier_field.id), None
        )
        if supplier_attr and supplier_attr.get("value"):
            existing_supplier = db.session.query(ItemAttribute).join(Item).filter(
                and_(
                    ItemAttribute.field_id == supplier_field.id,
                    ItemAttribute.value == supplier_attr["value"],
                    *base_filters,
                )
            ).first()
            if existing_supplier:
                duplicate_fields.append(f"供應商料號 '{supplier_attr['value']}' 已存在")

    if dst_field:
        dst_attr = next(
            (a for a in attributes if a.get("fieldId") == dst_field.id), None
        )
        if dst_attr and dst_attr.get("value"):
            existing_dst = db.session.query(ItemAttribute).join(Item).filter(
                and_(
                    ItemAttribute.field_id == dst_field.id,
                    ItemAttribute.value == dst_attr["value"],
                    *base_filters,
                )
            ).first()
            if existing_dst:
                duplicate_fields.append(f"DST料號 '{dst_attr['value']}' 已存在")

    return duplicate_fields
