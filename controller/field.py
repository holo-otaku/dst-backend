from models.series import ItemAttribute
from sqlalchemy import or_


def search_item_attribute_by_field_id_and_value(
    field_id: int, search_value: str = None
):
    """
    透過 field id 模糊搜尋 item_attribute 的 value。
    如果 search_value 為空，則返回該 field_id 的所有 item_attribute。
    """
    if not field_id:
        return {"code": 400, "msg": "Missing field_id", "data": []}

    try:
        query = ItemAttribute.query.filter(ItemAttribute.field_id == field_id)

        if search_value:
            query = query.filter(
                or_(
                    ItemAttribute.value.ilike(f"%{search_value}%"),
                )
            )

        # 使用 distinct() 確保不重複，並限制返回結果數量
        query = query.distinct(ItemAttribute.value).limit(100)
        results = query.all()
        return {"code": 200, "msg": "Success", "data": [item.value for item in results]}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": []}
