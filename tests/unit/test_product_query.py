"""Product search through the real route: filters, visibility, paging and ERP merge."""
from unittest.mock import patch, MagicMock

from controller import field_value
from models.archive import Archive
from models.series import Series, Field, Item
from models.shared import db
from tests.unit.test_security_fixes import ctx, user, auth  # noqa: F401


def seed(owner):
    s = Series(name="S", created_by=owner.id)
    db.session.add(s)
    db.session.flush()
    name = Field(name="name", data_type="string", series_id=s.id, sequence=1)
    price = Field(name="price", data_type="number", series_id=s.id, sequence=2)
    day = Field(name="day", data_type="datetime", series_id=s.id, sequence=3)
    part = Field(name="part", data_type="string", series_id=s.id, sequence=4, search_erp=True)
    db.session.add_all([name, price, day, part])
    db.session.flush()
    ids = []
    for n, p, d in [("apple", "5", "2025/01/01"), ("banana", "15", "2025/02/01"), ("cherry", "25", "2025/03/01")]:
        item = Item(series_id=s.id, attributes={
            str(name.id): n, str(price.id): p, str(day.id): d, str(part.id): f"P-{n}"})
        db.session.add(item)
        db.session.flush()
        ids.append(item.id)
    db.session.commit()
    return s.id, name.id, price.id, day.id, ids


def search(c, h, body, query=""):
    return c.post(f"/product/search{query}", json=body, headers=h).get_json()


def names(res):
    return [row["attributes"][0]["value"] for row in res["data"]]


def test_filters(ctx):
    _, c = ctx
    u = user("u", ["product.read"])
    sid, name, price, day, _ = seed(u)
    h = auth(u)
    assert names(search(c, h, {"seriesId": sid, "filters": [{"fieldId": name, "value": "an"}]})) == ["banana"]
    rng = [{"fieldId": price, "value": 10, "operation": "greater"},
           {"fieldId": price, "value": 20, "operation": "less"}]
    assert names(search(c, h, {"seriesId": sid, "filters": rng})) == ["banana"]
    # ISO and MM/DD/YY dates mean the same day
    for value in ["2025-02-01", "02/01/25"]:
        res = search(c, h, {"seriesId": sid, "filters": [{"fieldId": day, "value": value, "operation": "greater"}]})
        assert names(res) == ["banana", "cherry"]


def test_paging_sort_and_total(ctx):
    _, c = ctx
    u = user("u", ["product.read"])
    sid, _, price, _, _ = seed(u)
    res = search(c, auth(u), {"seriesId": sid}, f"?page=1&limit=2&sort={price},desc")
    assert names(res) == ["cherry", "banana"]
    assert res["totalCount"] == 3


def test_archive_visibility_matches_total(ctx):
    _, c = ctx
    reader = user("reader", ["product.read"])
    archiver = user("archiver", ["product.read", "archive.create"])
    sid, _, _, _, ids = seed(reader)
    reader_h, archiver_h = auth(reader), auth(archiver)
    db.session.add(Archive(item_id=ids[0], archived_by=archiver.id))
    db.session.commit()
    everything = {"seriesId": sid, "isDeleted": 2, "isArchived": 2}

    res = search(c, reader_h, everything)
    assert names(res) == ["banana", "cherry"] and res["totalCount"] == 2

    res = search(c, archiver_h, everything)
    assert res["totalCount"] == 3
    assert [row["hasArchive"] for row in res["data"]] == [True, False, False]


def test_erp_merged_by_search_erp_field(ctx):
    _, c = ctx
    u = user("u", ["product.read"])
    sid, _, _, _, _ = seed(u)
    erp = {"P-apple": [{"key": "交易狀態", "value": "A"}]}
    with patch("controller.product_query.read_erp", return_value=erp) as read_erp:
        res = search(c, auth(u), {"seriesId": sid})
    assert read_erp.call_args[0][0] == {"P-apple", "P-banana", "P-cherry"}
    assert [row["erp"] for row in res["data"]] == [erp["P-apple"], [], []]


def test_field_value_rules():
    field = MagicMock(data_type="number")
    field.name = "n"
    assert field_value.check(field, "1.5") == []
    assert field_value.check(field, "abc")
    field.data_type = "datetime"
    assert field_value.check(field, "2025/01/07") == []
    assert field_value.check(field, "not a date")
    assert field_value.normalize_date("01/07/25") == "2025/01/07"
    assert field_value.stored("datetime", "2025-01-07") == "2025/01/07"
    assert field_value.stored("boolean", "0") is False
    assert field_value.stored("number", "17.70") == "17.70"
    assert field_value.stored("string", "") is None
    assert field_value.present("boolean", False) is False
    assert field_value.present("picture", "7") == "/image/7"
    assert field_value.image_id("/image/7") == "7"
    assert field_value.image_id("data:image/png;base64,xx") is None


def test_blank_values_and_case_insensitive_filter(ctx):
    _, c = ctx
    u = user("u", ["product.read"])
    sid, name, price, day, _ = seed(u)
    db.session.add(Item(series_id=sid, attributes={str(name): "Apricot"}))
    # 舊資料裡無法解析的日期
    db.session.add(Item(series_id=sid, attributes={str(day): "32"}))
    db.session.commit()
    h = auth(u)
    assert names(search(c, h, {"seriesId": sid, "filters": [{"fieldId": name, "value": "AP"}]})) == ["apple", "Apricot"]
    # 沒有值的數字/日期不能讓排序或範圍查詢報錯；數字依大小排，不是字典序
    res = search(c, h, {"seriesId": sid}, f"?sort={price},asc")
    assert res["totalCount"] == 5
    assert [n for n in names(res) if n in ("apple", "banana", "cherry")] == ["apple", "banana", "cherry"]
    rng = [{"fieldId": price, "value": 10, "operation": "greater"}]
    assert names(search(c, h, {"seriesId": sid, "filters": rng})) == ["banana", "cherry"]
    rng = [{"fieldId": day, "value": "2025-02-01", "operation": "greater"}]
    assert names(search(c, h, {"seriesId": sid, "filters": rng})) == ["banana", "cherry"]


def test_boolean_field_create_and_filter(ctx):
    _, c = ctx
    u = user("u", ["product.read", "product.create"])
    sid, name, _, _, _ = seed(u)
    flag = Field(name="flag", data_type="boolean", series_id=sid, sequence=5)
    db.session.add(flag)
    db.session.commit()
    flag_id, h = flag.id, auth(u)
    res = c.post("/product", json=[{"seriesId": sid, "attributes": [
        {"fieldId": name, "value": "durian"}, {"fieldId": flag_id, "value": True}]}], headers=h)
    assert res.status_code == 201, res.get_json()
    created = Item.query.filter(Item.attributes[str(flag_id)].as_boolean().is_(True)).one()
    assert created.attributes[str(flag_id)] is True
    assert names(search(c, h, {"seriesId": sid, "filters": [{"fieldId": flag_id, "value": True}]})) == ["durian"]
    res = c.get(f"/product/{created.id}", headers=h).get_json()
    assert res["data"]["attributes"][-1]["value"] is True


def test_duplicate_part_number_check(ctx):
    _, c = ctx
    u = user("u", ["product.read", "product.create", "product.edit"])
    sid, name, _, _, ids = seed(u)
    dst = Field(name="DST料號", data_type="string", series_id=sid, sequence=5)
    db.session.add(dst)
    db.session.flush()
    # 要留著 item 的參照，MutableDict 才追蹤得到修改
    first = db.session.get(Item, ids[0])
    first.attributes[str(dst.id)] = "D-1"
    db.session.commit()
    dst_id, h = dst.id, auth(u)

    def create(value):
        return c.post("/product", json=[{"seriesId": sid, "attributes": [{"fieldId": dst_id, "value": value}]}], headers=h)
    assert create("D-2").status_code == 201
    assert create("D-1").status_code == 400
    # 編輯自己不算重複，改成別人的料號才算
    edit = c.patch("/product/edit", json=[{"itemId": ids[0], "attributes": [{"fieldId": dst_id, "value": "D-1"}]}], headers=h)
    assert edit.status_code == 200, edit.get_json()
    edit = c.patch("/product/edit", json=[{"itemId": ids[1], "attributes": [{"fieldId": dst_id, "value": "D-1"}]}], headers=h)
    assert edit.status_code == 400


def test_copy_and_field_changes_keep_attributes_in_sync(ctx):
    _, c = ctx
    u = user("u", ["product.read", "product.create", "series.edit"])
    sid, name, price, _, ids = seed(u)
    h = auth(u)
    res = c.post("/product/copy", json={"itemIds": [ids[0]]}, headers=h)
    assert res.status_code == 201, res.get_json()
    copied = db.session.get(Item, res.get_json()["data"][0]["id"])
    assert copied.attributes[str(name)] == "copy apple" and copied.attributes[str(price)] == "5"

    # 有值的欄位不能改型別；刪掉欄位後每個商品的值都要清掉
    changed = {"fields": [{"id": price, "name": "price", "dataType": "string"}]}
    assert c.patch(f"/series/{sid}", json=changed, headers=h).status_code == 400
    assert c.patch(f"/series/{sid}", json={"delete": [price]}, headers=h).status_code == 200
    db.session.expire_all()
    assert not Item.query.filter(Item.attributes[str(price)].as_string().is_not(None)).all()
