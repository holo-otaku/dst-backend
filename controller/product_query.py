"""產品查詢：搜尋與匯出共用。

負責篩選條件編譯、可見性（已刪除/封存/限制欄位）、分頁與總數、ERP 資料合併。
可見性規則只在這裡套用一次，資料列與 totalCount 用同一個 WHERE。
"""
from sqlalchemy import text

from controller import field_value
from controller.erp import read as read_erp
from models.archive import Archive
from models.series import Series, Field, ItemAttribute
from models.shared import db
from utils.permissions import check_field_permission

# 數字與日期的範圍比較運算子
_RANGE_OPERATORS = {"greater": ">=", "less": "<=", "equals": "=", "equal": "="}


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

    where, parameters = _compile_where(
        series_id, filters, fields, query_is_deleted, query_is_archived
    )

    sql_query = f"SELECT item.id, item.is_deleted FROM item WHERE {where}"
    if sort_field_id is not None:
        # 值都存成字串，數字欄位要轉型才不會變成字典序
        sort_value = "CAST(value AS float)" if fields[sort_field_id].data_type == "number" else "value"
        sql_query += (
            f" ORDER BY (SELECT {sort_value} FROM item_attribute"
            " WHERE item_id = item.id AND field_id = :sort_field_id)"
        )
        if sort_order == "desc":
            sql_query += " DESC"
        parameters["sort_field_id"] = sort_field_id
    if limit is not None:
        sql_query += " LIMIT :limit OFFSET :offset"
        parameters["limit"] = limit
        parameters["offset"] = (page - 1) * limit

    items = db.session.execute(text(sql_query), parameters).fetchall()
    total_count = db.session.execute(
        text(f"SELECT COUNT(item.id) FROM item WHERE {where}"), parameters
    ).scalar()

    rows = _build_rows(series, items, fields, can_read_limit)
    return rows, total_count, fields


def _compile_where(series_id, filters, fields, is_deleted, is_archived):
    conditions = ["item.series_id = :series_id"]
    parameters = {"series_id": series_id}

    if is_deleted is not None:
        conditions.append("item.is_deleted = :is_deleted")
        parameters["is_deleted"] = is_deleted

    if is_archived is not None:
        conditions.append(
            ("item.id IN" if is_archived == 1 else "item.id NOT IN")
            + " (SELECT item_id FROM archive)"
        )

    for index, filter_criteria in enumerate(filters):
        field = fields[filter_criteria["fieldId"]]
        operation = filter_criteria.get("operation", "equals")
        value = filter_criteria["value"]
        field_param, value_param = f"field_id{index}", f"value{index}"
        data_type = field.data_type.lower()

        if data_type == "string":
            expression = f"item_attribute.value LIKE :{value_param}"
            value = f"%{value}%"
        elif data_type == "number" and operation in ("greater", "less"):
            expression = f"CAST(item_attribute.value AS float) {_RANGE_OPERATORS[operation]} :{value_param}"
        elif data_type == "datetime" and operation in _RANGE_OPERATORS:
            # 只比較日期部分
            expression = f"DATE(item_attribute.value) {_RANGE_OPERATORS[operation]} DATE(:{value_param})"
            value = field_value.normalize_date(value) or value
        else:
            expression = f"item_attribute.value = :{value_param}"
            if data_type == "datetime":
                value = field_value.normalize_date(value) or value

        conditions.append(
            f"item.id IN (SELECT item_id FROM item_attribute"
            f" WHERE item_attribute.field_id = :{field_param} AND {expression})"
        )
        parameters[field_param] = field.id
        parameters[value_param] = value

    return " AND ".join(conditions), parameters


def _build_rows(series, items, fields, can_read_limit):
    item_ids = [item_id for item_id, _ in items]
    attributes = {
        (attr.item_id, attr.field_id): attr.value
        for attr in db.session.query(ItemAttribute).filter(ItemAttribute.item_id.in_(item_ids))
    }
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
        return field_value.present(field.data_type, attributes.get((item_id, field.id)))

    # 沒有料號的產品也會拿到一組空白 ERP 欄位（key 為 None），前端靠它決定 ERP 欄位
    erp_data_map = read_erp(
        {value_of(item_id, field) for item_id in item_ids for field in erp_key_fields},
        series.id,
    )

    rows = []
    for item_id, is_deleted in items:
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
                        "fieldId": str(field.id),
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
