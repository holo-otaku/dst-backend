from models.series import ItemAttribute, Field, Item
from models.archive import Archive
from sqlalchemy import or_, distinct, func
from models.shared import db
from utils.permissions import check_field_permission
from modules.exception import handle_exceptions


@handle_exceptions
def search_item_attribute_by_field_id_and_value(
    field_id: int, search_value: str | None = None
):
    """
    透過 field id 模糊搜尋 item_attribute 的 value。
    如果 search_value 為空，則返回該 field_id 的所有 item_attribute。
    包含 archive 權限檢查，過濾掉已歸檔商品的資料（如果用戶沒有 archive 權限）。
    """
    if not field_id:
        return {"code": 400, "msg": "Missing field_id", "data": []}

    # 檢查用戶是否有查看 archive 的權限
    has_archive_permission = check_field_permission("archive.create")

    # 構建基本查詢
    base_query = db.session.query(distinct(ItemAttribute.value)).join(Item).filter(
        ItemAttribute.field_id == field_id,
        ItemAttribute.value.is_not(None)
    )

    # 如果用戶沒有 archive 權限，過濾掉已歸檔的商品
    if not has_archive_permission:
        # 子查詢找出所有已歸檔的 item_id
        archived_items_subquery = db.session.query(Archive.item_id).subquery()
        base_query = base_query.filter(~Item.id.in_(archived_items_subquery))

    # 添加搜尋條件
    if search_value:
        search_value = search_value.strip()  # 去除搜索值的首尾空格
        base_query = base_query.filter(ItemAttribute.value.ilike(f"%{search_value}%"))

    # 執行查詢並限制結果
    results = base_query.limit(100).all()

    # results 是 tuple 的 list，需要提取第一個元素並處理空格
    raw_values = [result[0] for result in results]
    
    # 使用 set 來去除重複值（包括去除空格後的重複）
    unique_values = set()
    for value in raw_values:
        if value:  # 確保值不是 None
            trimmed_value = value.strip()
            if trimmed_value:  # 確保 trim 後不是空字符串
                unique_values.add(trimmed_value)
    
    # 轉換為 list 並排序
    unique_values = sorted(list(unique_values))

    return {"code": 200, "msg": "Success", "data": unique_values}
