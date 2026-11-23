"""產品查詢：搜尋、匯出與單筆讀取共用。

負責篩選條件編譯、可見性（已刪除/封存/限制欄位）、分頁與總數、ERP 資料合併。
可見性規則只在這裡套用，資料列與 totalCount 用同一個 WHERE；單筆讀取與寫入用 visible_item()。
"""
import operator

from sqlalchemy import func, select

from controller import field_value
from controller.erp import read as read_erp
from models.archive import Archive
from models.series import Series, Field, Item
from models.shared import db
from utils.permissions import check_field_permission

# 數字與日期的範圍比較
_RANGE_OPERATORS = {"greater": operator.ge, "less": operator.le, "equals": operator.eq, "equal": operator.eq}


def search(data, page=1, limit=None, sort=None):
    """
    - data: request body，包含 seriesId、filters、isDeleted、isArchived
      （isDeleted/isArchived：0 否、1 是、2 全部）
    - limit: None 表示不分頁（匯出）
    - sort: "fieldId,asc|desc"
    回傳 (rows, total_count, fields)，fields 為 {field_id: Field}
    """
    series_id = data.get("seriesId")
    if not series_id:
        raise ValueError("SeriesId not found")

    is_deleted = data.get("isDeleted", 0)
    if is_deleted not in [0, 1, 2]:
        raise ValueError("Input body error")

    is_archived = data.get("isArchived", 0)
    if is_archived not in [0, 1, 2]:
        raise ValueError("isArchived must be 0, 1 or 2")

    series = db.session.query(Series).filter_by(id=series_id, status=1).first()
    if not series:
        raise ValueError("Series not found")

    fields = {
        field.id: field
        for field in db.session.query(Field).filter(Field.series_id == series_id)
    }

    # 沒有 limit-field.read 不能用 limit 欄位篩選或排序，否則可以推出隱藏的值
    can_read_limit = check_field_permission("limit-field.read")

    def is_hidden(field_id):
        return field_id not in fields or (fields[field_id].is_limit_field and not can_read_limit)

    sort_field_id, sort_order = None, None
    if sort:
        sort_parts = sort.split(",")
        if len(sort_parts) != 2:
            raise ValueError("Invalid sort parameter")
        sort_field_id, sort_order = int(sort_parts[0]), sort_parts[1].lower()
        if is_hidden(sort_field_id):
            raise ValueError("Invalid sort parameter")

    filters = data.get("filters", [])
    for filter_criteria in filters:
        field_id = filter_criteria["fieldId"]
        if is_hidden(field_id):
            raise ValueError(f"Invalid fieldId: {field_id}")
        type_err = field_value.check(fields[field_id], filter_criteria["value"])
        if type_err:
            raise ValueError(type_err)

    # 2 表示不限制
    query_is_deleted = None if is_deleted == 2 else is_deleted
    query_is_archived = None if is_archived == 2 else is_archived
    # 沒有封存權限時一律排除封存品，資料列與 totalCount 都看不到
    if not check_field_permission("archive.create"):
        query_is_archived = 0

    where = _compile_where(series_id, filters, fields, query_is_deleted, query_is_archived)

    query = select(Item.id, Item.is_deleted, Item.attributes).where(*where)
    if sort_field_id is not None:
        sort_column = field_value.sql(sort_field_id, fields[sort_field_id].data_type)
        query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column)
    # MySQL 沒有 ORDER BY 時依 id 回傳；PG 不保證順序，分頁會重複或漏
    query = query.order_by(Item.id)
    if limit is not None:
        query = query.limit(limit).offset((page - 1) * limit)

    items = db.session.execute(query).all()
    total_count = db.session.scalar(select(func.count()).select_from(Item).where(*where))

    rows = _build_rows(series, items, fields, can_read_limit)
    return rows, total_count, fields


def visible_item(item_id):
    """目前使用者看得到的 Item；不存在、series 已刪除、或沒封存權限時的封存品都回傳 None。
    已刪除（is_deleted）的產品仍然看得到。"""
    item = db.session.get(Item, item_id) if item_id else None
    if not item or item.series.status == 0:
        return None
    if not check_field_permission("archive.create") and _is_archived(item.id):
        return None
    return item


def get(item_id):
    """單筆產品，格式與 search() 的資料列相同；看不到時回傳 None。"""
    item = visible_item(item_id)
    if not item:
        return None
    fields = {field.id: field for field in item.series.fields}
    can_read_limit = check_field_permission("limit-field.read")
    return _build_rows(item.series, [(item.id, item.is_deleted, item.attributes)], fields, can_read_limit)[0]


def _is_archived(item_id):
    return db.session.query(Archive.item_id).filter(Archive.item_id == item_id).first() is not None


def _compile_where(series_id, filters, fields, is_deleted, is_archived):
    conditions = [Item.series_id == series_id]

    if is_deleted is not None:
        conditions.append(Item.is_deleted.is_(bool(is_deleted)))

    if is_archived is not None:
        archived = Item.id.in_(select(Archive.item_id))
        conditions.append(archived if is_archived == 1 else ~archived)

    for filter_criteria in filters:
        field = fields[filter_criteria["fieldId"]]
        operation = filter_criteria.get("operation", "equals")
        data_type = field.data_type.lower()
        column = field_value.sql(field.id, data_type)
        value = field_value.stored(data_type, filter_criteria["value"])
        if value is None:
            continue

        if data_type == "string":
            conditions.append(column.ilike(f"%{value}%"))
        elif data_type == "number":
            compare = _RANGE_OPERATORS.get(operation, operator.eq)
            conditions.append(compare(column, float(value)))
        elif data_type == "datetime" and operation in _RANGE_OPERATORS:
            # YYYY/MM/DD 的字串比較就是日期先後；舊資料有不是日期的值（例如 "32"），不能算進範圍
            conditions.append(column.like("____/__/__"))
            conditions.append(_RANGE_OPERATORS[operation](column, value))
        elif data_type == "boolean":
            conditions.append(column.is_(value))
        else:
            conditions.append(column == value)

    return conditions


def _build_rows(series, items, fields, can_read_limit):
    item_ids = [item_id for item_id, _, _ in items]
    attributes = {item_id: item_attributes for item_id, _, item_attributes in items}
    archived_ids = {
        item_id
        for (item_id,) in db.session.query(Archive.item_id).filter(Archive.item_id.in_(item_ids))
    }

    ordered_fields = sorted(fields.values(), key=lambda field: field.sequence)
    visible_fields = [
        field
        for field in ordered_fields
        if not field.is_erp and (not field.is_limit_field or can_read_limit)
    ]
    erp_key_fields = [field for field in ordered_fields if field.search_erp]

    def value_of(item_id, field):
        return field_value.present(field.data_type, attributes[item_id].get(str(field.id)))

    # 沒有料號的產品也會拿到一組空白 ERP 欄位（key 為 None），前端靠它決定 ERP 欄位
    erp_data_map = read_erp(
        {value_of(item_id, field) for item_id in item_ids for field in erp_key_fields},
        series.id,
    )

    rows = []
    for item_id, is_deleted, _ in items:
        erp_data = []
        for field in erp_key_fields:
            erp_data += erp_data_map.get(value_of(item_id, field), [])
        rows.append(
            {
                "itemId": item_id,
                "seriesId": series.id,
                "seriesName": series.name,
                "attributes": [
                    {
                        "fieldId": field.id,
                        "fieldName": field.name,
                        "dataType": field.data_type,
                        "value": value_of(item_id, field),
                    }
                    for field in visible_fields
                ],
                "erp": erp_data,
                "isDeleted": bool(is_deleted),
                "hasArchive": item_id in archived_ids,
            }
        )
    return rows
