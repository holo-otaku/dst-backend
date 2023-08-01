from flask import current_app
from models.mssql import Connect


def read(prod_no):
    conn = None
    cursor = None
    try:
        conn = Connect(current_app.config["DST_MSSQL"])
        cursor = conn.cursor()
        sql_query = """
            SELECT TOP 1 FACT_NO, PROD_NO, PROD_NAME, PROD_C, PROD_CT, KEYI_D, LEAD_TIME, FIZO_D, PROD_STAT
            FROM PROD
            WHERE PROD_NO = ?"""
        cursor.execute(sql_query, (prod_no,))

        results = cursor.fetchall()

        data = []

        for row in results:
            data.append({"key": "廠商編號", "value": str(row.FACT_NO)})
            data.append({"key": "產品編號", "value": str(row.PROD_NO)})
            data.append({"key": "品名規格", "value": str(row.PROD_NAME)})
            data.append({"key": "標準進價(進貨幣別)", "value": str(row.PROD_C)})
            data.append({"key": "實際單位總成本(本地幣)", "value": str(row.PROD_CT)})
            data.append({"key": "建檔日期", "value": row.KEYI_D})
            data.append({"key": "LeadTime(天)", "value": str(row.LEAD_TIME)})
            data.append({"key": "停產日期", "value": str(row.FIZO_D)})
            data.append({"key": "交易狀態", "value": str(row.PROD_STAT)})

        return data
    except Exception as e:
        current_app.logger.error(e)

        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
