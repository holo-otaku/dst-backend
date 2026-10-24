"""Field 值的型別規則：每個 data_type 怎麼驗證、標準化、回傳給前端。

ItemAttribute.value 一律存字串，所以讀寫兩端都要經過這裡。
"""
import base64
import io
from datetime import datetime

from PIL import Image as PILImage

from models.mapping_table import data_type_map

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
    """把支援的日期格式轉成 YYYY-MM-DD，無法解析時回傳 None。"""
    if not value:
        return None
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).strftime("%Y-%m-%d")
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
        decoded_data = base64.b64decode(value.split(",")[1])
        img = PILImage.open(io.BytesIO(decoded_data))
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


def present(data_type, value):
    """把資料庫裡的字串轉成 API 回傳的值。"""
    if not value:
        return None
    if data_type == "number":
        return str(value)
    if data_type == "boolean":
        return bool(int(value))
    if data_type == "picture":
        return f"{IMAGE_URL_PREFIX}{value}"
    return value


def image_id(url):
    """present() 的反向：'/image/<id>' -> '<id>'，不是圖片網址時回傳 None。"""
    if isinstance(url, str) and url.startswith(IMAGE_URL_PREFIX):
        return url[len(IMAGE_URL_PREFIX):]
    return None
