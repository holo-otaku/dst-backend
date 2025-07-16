from flask import current_app
from models.mssql import Connect
from models.series import Field
from models.shared import db
from utils.permissions import check_field_permission

def get_erp_fields_metadata():
    """
    Returns a list of ERP field metadata (name, data_type).
    """
    return [
        {"name": "標準進價(進貨幣別)", "dataType": "string"},
        {"name": "實際單位總成本(本地幣)", "dataType": "string"},
        {"name": "進貨幣別欄位", "dataType": "string"},
        {"name": "建檔日期", "dataType": "datetime"},
        {"name": "LeadTime(天)", "dataType": "string"},
        {"name": "停產日期", "dataType": "datetime"},
        {"name": "交易狀態", "dataType": "string"},
    ]


def read(product_numbers, series_id=None):
    data_map = {}

    if not product_numbers:
        return data_map

    placeholders = ",".join(["?" for _ in product_numbers])
    sql_query = f"""
        SELECT PROD_NO, PROD_C, PROD_CT, DOLR_TI, KEYI_D, LEAD_TIME, FIZO_D, PROD_STAT
        FROM PROD
        WHERE PROD_NO IN ({placeholders})
    """
    conn = None
    cursor = None
    try:
        conn = Connect(current_app.config["DST_MSSQL"])
        cursor = conn.cursor()
        cursor.execute(sql_query, tuple(product_numbers))

        results = cursor.fetchall()

        for row in results:
            # 完整的 ERP 欄位資料
            data = [
                {"key": "標準進價(進貨幣別)", "value": str(row.PROD_C)},
                {"key": "實際單位總成本(本地幣)", "value": str(row.PROD_CT)},
                {"key": "進貨幣別欄位", "value": str(row.DOLR_TI)},
                {"key": "建檔日期", "value": row.KEYI_D},
                {"key": "LeadTime(天)", "value": str(row.LEAD_TIME)},
                {"key": "停產日期", "value": str(row.FIZO_D)},
                {"key": "交易狀態", "value": str(row.PROD_STAT)},
            ]

            data_map[row.PROD_NO] = data

    except Exception as e:
        current_app.logger.error(e)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Ensure all product_numbers have a result in the data_map
    for product_no in product_numbers:
        if product_no not in data_map:
            default_data = [
                {"key": "標準進價(進貨幣別)", "value": ""},
                {"key": "實際單位總成本(本地幣)", "value": ""},
                {"key": "進貨幣別欄位", "value": ""},
                {"key": "建檔日期", "value": ""},
                {"key": "LeadTime(天)", "value": ""},
                {"key": "停產日期", "value": ""},
                {"key": "交易狀態", "value": ""},
            ]
            data_map[product_no] = default_data

    # 最後根據權限過濾 ERP 欄位
    if series_id:
        data_map = _filter_erp_fields_by_permission(data_map, series_id)

    return data_map


def _filter_erp_fields_by_permission(data_map, series_id):
    """根據權限過濾 ERP 欄位"""
    # 取得 ERP 欄位的權限設定
    erp_fields = db.session.query(Field).filter(
        Field.series_id == series_id,
        Field.is_erp == True
    ).all()
    
    erp_fields_permission = {}
    for field in erp_fields:
        # 檢查是否為限制欄位
        has_permission = True
        if field.is_limit_field:
            has_permission = check_field_permission("limit-field.read")
        erp_fields_permission[field.name] = has_permission
    print(erp_fields_permission)
    # 過濾每個產品的 ERP 欄位
    filtered_data_map = {}
    for product_no, field_data_list in data_map.items():
        filtered_fields = []
        for field_data in field_data_list:
            field_name = field_data["key"]
            # 檢查權限，預設為 True（向後兼容）
            if erp_fields_permission.get(field_name, True):
                filtered_fields.append(field_data)
        filtered_data_map[product_no] = filtered_fields
    
    return filtered_data_map
