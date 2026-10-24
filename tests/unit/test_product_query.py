"""Product search through the real route: filters, visibility, paging and ERP merge."""
from unittest.mock import patch, MagicMock

from controller import field_value
from models.archive import Archive
from models.series import Series, Field, Item, ItemAttribute
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
    for n, p, d in [("apple", "5", "2025-01-01"), ("banana", "15", "2025-02-01"), ("cherry", "25", "2025-03-01")]:
        item = Item(series_id=s.id)
        db.session.add(item)
        db.session.flush()
        db.session.add_all([ItemAttribute(item_id=item.id, field_id=name.id, value=n),
                            ItemAttribute(item_id=item.id, field_id=price.id, value=p),
                            ItemAttribute(item_id=item.id, field_id=day.id, value=d),
                            ItemAttribute(item_id=item.id, field_id=part.id, value=f"P-{n}")])
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
    assert field_value.normalize_date("01/07/25") == "2025-01-07"
    assert field_value.present("boolean", "0") is False
    assert field_value.present("picture", "7") == "/image/7"
    assert field_value.image_id("/image/7") == "7"
    assert field_value.image_id("data:image/png;base64,xx") is None
