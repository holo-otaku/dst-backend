"""產品寫入：新增、複製、編輯都從這裡把值寫進 Item.attributes。

每個操作先驗證整筆資料，全部通過才動 Item 與圖片；不 commit，由呼叫端在整批成功後 commit 一次。
驗證失敗丟 WriteError(code, msg)。
"""
import base64

from sqlalchemy import func

from controller import field_value, image_store
from models.series import Series, Field, Item
from models.shared import db
from utils.permissions import check_field_permission

# 同一個 series 裡不能重複的料號欄位（不分大小寫，忽略已刪除的產品）
UNIQUE_FIELD_NAMES = ("供應商料號", "DST料號")


class WriteError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code
        self.msg = msg


def create(series_id, attributes):
    """attributes: [{"fieldId", "value"}]，picture 的 value 是 base64 data URL。"""
    if not series_id:
        raise WriteError(400, "Incomplete data")
    series = db.session.get(Series, series_id)
    if not series or series.status == 0:
        raise WriteError(404, "Series not found")

    fields = _fields(series_id)
    sent = {attribute.get("fieldId") for attribute in attributes}
    missing = [field.name for field in fields if field.is_required and field.id not in sent]
    if missing:
        raise WriteError(400, f"Missing required field: {missing}")
    values = _values(fields, attributes)
    _check_unique(series_id, values)

    item = Item(series_id=series_id, attributes={})
    db.session.add(item)
    db.session.flush()
    for field, value in values:
        if field.data_type == "picture" and value:
            value = image_store.save(_decode(value))
        _assign(item, field, value)
    return item


def copy(source):
    """複製一筆產品：圖片複製成新檔案，第一個有值的字串欄位前面加 "copy "。"""
    item = Item(series_id=source.series_id, attributes={})
    db.session.add(item)
    db.session.flush()
    prefixed = False
    for field in _fields(source.series_id):
        value = source.attributes.get(str(field.id))
        if field.data_type == "picture" and value:
            value = image_store.copy(value)
        elif field.data_type == "string" and value and not prefixed:
            value = f"copy {value}"
            prefixed = True
        _assign(item, field, value)
    return item


def edit(item, attributes):
    """只改傳進來的欄位；空值刪掉該欄位，picture 換新圖時刪掉舊圖。"""
    fields = {field.id: field for field in _fields(item.series_id)}
    can_read_limit = check_field_permission("limit-field.read")
    for attribute in attributes:
        field_id = attribute.get("fieldId")
        if not field_id:
            raise WriteError(400, "Incomplete attribute data")
        field = fields.get(field_id)
        # 看不到的限制欄位也不能改
        if not field or (field.is_limit_field and not can_read_limit):
            raise WriteError(404, f"field_id:{field_id} not found")
    values = _values([fields[a["fieldId"]] for a in attributes], attributes)
    _check_unique(item.series_id, values, exclude_item_id=item.id)

    for field, value in values:
        if field.data_type == "picture":
            old = item.attributes.get(str(field.id))
            if old:
                image_store.delete(old)
            if value:
                value = image_store.save(_decode(value))
        _assign(item, field, value)


def _fields(series_id):
    return db.session.query(Field).filter(Field.series_id == series_id).order_by(Field.sequence).all()


def _values(fields, attributes):
    """每個欄位配上送來的值並檢查型別，回傳 [(field, value)]。"""
    by_id = {attribute.get("fieldId"): attribute.get("value") for attribute in attributes}
    values = []
    for field in fields:
        value = by_id.get(field.id)
        type_err = field_value.check(field, value)
        if type_err:
            raise WriteError(400, type_err)
        values.append((field, value))
    return values


def _check_unique(series_id, values, exclude_item_id=None):
    conditions = [Item.series_id == series_id, Item.is_deleted.is_(False)]
    if exclude_item_id is not None:
        conditions.append(Item.id != exclude_item_id)
    duplicates = []
    for field, value in values:
        if field.name not in UNIQUE_FIELD_NAMES or not value:
            continue
        exists = db.session.query(Item.id).filter(
            func.lower(field_value.sql(field.id, "string")) == str(value).lower(),
            *conditions,
        ).first()
        if exists:
            duplicates.append(f"{field.name} '{value}' 已存在")
    if duplicates:
        raise WriteError(400, f"Duplicate values found: {duplicates}")


def _decode(data_url):
    return base64.b64decode(data_url.split(",", 1)[-1])


def _assign(item, field, value):
    value = field_value.stored(field.data_type, value)
    if value is None:
        item.attributes.pop(str(field.id), None)
    else:
        item.attributes[str(field.id)] = value
