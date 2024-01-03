from flask import current_app
from models.mssql import Connect


def read(product_numbers):
    data_map = {}

    if not product_numbers:
        return data_map

    placeholders = ",".join(["?" for _ in product_numbers])
    sql_query = f"""
        SELECT PROD_NAME, PROD_C, PROD_CT, DOLR_TI, KEYI_D, LEAD_TIME, FIZO_D, PROD_STAT
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
            data = []
            data.append({"key": "品名規格", "value": str(row.PROD_NAME)})
            data.append({"key": "標準進價(進貨幣別)", "value": str(row.PROD_C)})
            data.append({"key": "實際單位總成本(本地幣)", "value": str(row.PROD_CT)})
            data.append({"key": "進貨幣別欄位", "value": str(row.DOLR_TI)})
            data.append({"key": "建檔日期", "value": row.KEYI_D})
            data.append({"key": "LeadTime(天)", "value": str(row.LEAD_TIME)})
            data.append({"key": "停產日期", "value": str(row.FIZO_D)})
            data.append({"key": "交易狀態", "value": str(row.PROD_STAT)})

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
            default_data = []
            default_data.append({"key": "品名規格", "value": ""})
            default_data.append({"key": "標準進價(進貨幣別)", "value": ""})
            default_data.append({"key": "實際單位總成本(本地幣)", "value": ""})
            default_data.append({"key": "進貨幣別欄位", "value": str(row.DOLR_TI)})
            default_data.append({"key": "建檔日期", "value": ""})
            default_data.append({"key": "LeadTime(天)", "value": ""})
            default_data.append({"key": "停產日期", "value": ""})
            default_data.append({"key": "交易狀態", "value": ""})

            data_map[product_no] = default_data

    return data_map
