from models.series import ItemAttribute
from sqlalchemy import or_, distinct
from models.shared import db


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
        # 使用 SQL 的 DISTINCT 直接在資料庫層面去重，避免載入大量重複資料
        if search_value:
            # 有搜尋條件時
            results = db.session.query(distinct(ItemAttribute.value)).filter(
                ItemAttribute.field_id == field_id,
                ItemAttribute.value.ilike(f"%{search_value}%"),
                ItemAttribute.value.is_not(None)
            ).limit(100).all()
        else:
            # 沒有搜尋條件時，取該 field_id 的所有不重複值
            results = db.session.query(distinct(ItemAttribute.value)).filter(
                ItemAttribute.field_id == field_id,
                ItemAttribute.value.is_not(None)
            ).limit(100).all()
        
        # results 是 tuple 的 list，需要提取第一個元素
        unique_values = [result[0] for result in results]
        
        return {"code": 200, "msg": "Success", "data": unique_values}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": []}
