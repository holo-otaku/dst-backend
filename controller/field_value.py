"""Field 值的型別規則：每個 data_type 怎麼驗證、存進 Item.attributes、查詢、回傳給前端。

Item.attributes 是 {str(field_id): 值}：布林存 true/false，其他型別存字串
（數字保留使用者輸入的格式，例如 "17.70"；日期統一成 YYYY/MM/DD，字串比較就是日期先後）。
"""
import base64
import io
from datetime import datetime

from PIL import Image as PILImage
from sqlalchemy import Float, cast

from models.mapping_table import data_type_map
from models.series import Item

IMAGE_URL_PREFIX = "/image/"

DATE_FORMATS = [
    "%Y/%m/%d",  # 2025/01/07
    "%m/%d/%y",  # 01/07/25
    "%m/%d/%Y",  # 01/07/2025
    "%Y-%m-%d",  # 2025-01-07
    "%d/%m/%Y",  # 07/01/2025
    "%d-%m-%Y",  # 07-01-2025
]


def normalize_date(value):
    """把支援的日期格式轉成 YYYY/MM/DD，無法解析時回傳 None。"""
    if not value:
        return None
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).strftime("%Y/%m/%d")
        except ValueError:
            continue
    return None


def check(field, value):
    """回傳型別錯誤訊息的 list，沒有錯誤時為空。"""
    if not value:
        return []

    data_type = field.data_type.lower()
    error = [
        f"Incorrect data type for field: {field.name}. Expected {data_type}, got {type(value).__name__}."
    ]

    if data_type not in data_type_map:
        return error

    if data_type == "picture":
        # base64 data URL，只接受 jpeg/png
        try:
            decoded_data = base64.b64decode(value.split(",")[1])
            img = PILImage.open(io.BytesIO(decoded_data))
        except (IndexError, ValueError, OSError):
            return error
        if img.format is None or img.format.lower() not in ["jpeg", "jpg", "png"]:
            return error
    elif data_type == "datetime":
        if normalize_date(value) is None:
            return error
    elif data_type == "number":
        try:
            float(value)
        except (TypeError, ValueError):
            return error

    return []


def stored(data_type, value):
    """寫入或比對 Item.attributes 的值，空值回傳 None（不存 key）。"""
    if value is None or value == "":
        return None
    if data_type == "boolean":
        return value in (True, "1", "true")
    if data_type == "datetime":
        return normalize_date(value) or value
    return str(value)


def sql(field_id, data_type):
    """Item.attributes 裡某個欄位的 SQL 運算式，可直接比較、排序。"""
    value = Item.attributes[str(field_id)]
    if data_type == "number":
        # as_float() 在 SQLite 不會轉型，字串會跟數字比
        return cast(value.as_string(), Float)
    if data_type == "boolean":
        return value.as_boolean()
    return value.as_string()


def present(data_type, value):
    """把 Item.attributes 裡的值轉成 API 回傳的值。"""
    if value is None:
        return None
    if data_type == "picture":
        return f"{IMAGE_URL_PREFIX}{value}"
    return value


def image_id(url):
    """present() 的反向：'/image/<id>' -> '<id>'，不是圖片網址時回傳 None。"""
    if isinstance(url, str) and url.startswith(IMAGE_URL_PREFIX):
        return url[len(IMAGE_URL_PREFIX):]
    return None
