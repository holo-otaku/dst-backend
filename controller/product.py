from flask import jsonify, make_response, request
from controller import field_value, image_store, product_query, product_write
from models.series import Item
from models.shared import db
from utils.permissions import has_permission
from modules.exception import handle_exceptions
import xlsxwriter
from io import BytesIO
from flask import send_file


@handle_exceptions
def read(product_id):
    if not product_id:
        return make_response(
            jsonify({"code": 400, "msg": "Product ID is required"}), 400
        )

    result = product_query.get(product_id)
    if not result:
        return make_response(jsonify({"code": 404, "msg": "Product not found"}), 404)

    response = make_response(
        jsonify({"code": 200, "msg": "Success", "data": result}), 200
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@handle_exceptions
def create(data):
    try:
        items = [
            product_write.create(item_data.get("seriesId"), item_data.get("attributes", []))
            for item_data in data
        ]
    except product_write.WriteError as e:
        return _error(e.code, e.msg)

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
    # 前端可能送字串 id（MySQL 會自動轉，PG 不會）
    item_ids = [int(item_id) for item_id in item_ids]

    sources = {item_id: product_query.visible_item(item_id) for item_id in item_ids}
    missing_ids = [item_id for item_id, item in sources.items() if not item]
    if missing_ids:
        return _error(404, f"Item(s) not found: {missing_ids}")

    new_items = [product_write.copy(item) for item in sources.values()]

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
                            image_path = image_store.path(image_id)
                            if image_path:
                                # 插入圖片到 Excel
                                worksheet.insert_image(row_idx, col_idx, image_path, {
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
    if not data:
        return _error(400, "Empty data")

    for item_data in data:
        item_id = item_data.get("itemId")
        is_deleted = item_data.get("isDeleted")
        if not item_id:
            return _error(400, "Incomplete data")

        item = product_query.visible_item(item_id)
        if not item:
            return _error(404, "Item not found")

        if is_deleted in [0, 1]:
            # 刪除/還原和 DELETE /product/delete 一樣需要 product.delete
            if not has_permission("product.delete"):
                return _error(403, "Permission denied")
            item.is_deleted = is_deleted

        try:
            product_write.edit(item, item_data.get("attributes", []))
        except product_write.WriteError as e:
            return _error(e.code, e.msg)

    # 整批都通過才 commit；中途回錯誤時 handle_exceptions 關掉 session，前面的修改都不會寫入
    db.session.commit()

    return make_response(jsonify({"code": 200, "msg": "ItemAttributes updated"}), 200)


@handle_exceptions
def delete(data):
    if not data or "itemId" not in data:
        return make_response(jsonify({"code": 400, "msg": "Invalid data"}), 400)

    # 前端可能送字串 id（MySQL 會自動轉，PG 不會）
    item_ids = [int(item_id) for item_id in data["itemId"]]

    items_to_delete = db.session.query(Item).filter(Item.id.in_(item_ids)).all()

    for item in items_to_delete:
        item.is_deleted = 1

    db.session.commit()

    return make_response(jsonify({"code": 200, "msg": "Items deleted"}), 200)


def _error(code, msg):
    return make_response(jsonify({"code": code, "msg": msg}), code)
