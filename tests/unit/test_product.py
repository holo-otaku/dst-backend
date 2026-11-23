"""Product create/read/edit/copy/delete through the real routes, DB and image directory."""
import os

from models.archive import Archive
from models.image import Image
from models.series import Series, Field, Item
from models.shared import db
from tests.unit.test_api_smoke import png, png_data_url
from tests.unit.test_security_fixes import ctx, user, auth  # noqa: F401

ALL = ["product.read", "product.create", "product.edit", "product.delete",
       "archive.create", "limit-field.read"]


def seed(owner):
    s = Series(name="S", created_by=owner.id)
    db.session.add(s)
    db.session.flush()
    fields = [
        Field(name="供應商料號", data_type="string", series_id=s.id, sequence=1, is_required=True),
        Field(name="DST料號", data_type="string", series_id=s.id, sequence=2),
        Field(name="price", data_type="number", series_id=s.id, sequence=3),
        Field(name="cost", data_type="number", series_id=s.id, sequence=4, is_limit_field=True),
        Field(name="pic", data_type="picture", series_id=s.id, sequence=5),
    ]
    db.session.add_all(fields)
    db.session.commit()
    return s.id, {f.name: f.id for f in fields}


def create(c, h, sid, fid, **values):
    attrs = [{"fieldId": fid[name], "value": value} for name, value in values.items()]
    return c.post("/product", json=[{"seriesId": sid, "attributes": attrs}], headers=h)


def files(app):
    return sorted(os.listdir(app.config["IMG_PATH"]))


def test_create_validates_before_writing(ctx):
    app, c = ctx
    u = user("u", ALL)
    sid, fid = seed(u)
    h = auth(u)
    assert create(c, h, sid, fid, price="1").get_json()["msg"] == "Missing required field: ['供應商料號']"
    assert create(c, h, 999, fid, 供應商料號="S").status_code == 404
    assert create(c, h, sid, fid, 供應商料號="S", price="abc").status_code == 400
    assert create(c, h, sid, fid, 供應商料號="S-1", DST料號="D-1").status_code == 201
    res = create(c, h, sid, fid, 供應商料號="s-1")
    assert res.status_code == 400 and "供應商料號 's-1' 已存在" in res.get_json()["msg"]


def test_failed_batch_create_leaves_no_rows_or_files(ctx):
    app, c = ctx
    u = user("u", ALL)
    sid, fid = seed(u)
    body = [{"seriesId": sid, "attributes": [{"fieldId": fid["供應商料號"], "value": "A"},
                                             {"fieldId": fid["pic"], "value": png_data_url()}]},
            {"seriesId": sid, "attributes": [{"fieldId": fid["供應商料號"], "value": "B"},
                                             {"fieldId": fid["price"], "value": "abc"}]}]
    assert c.post("/product", json=body, headers=auth(u)).status_code == 400
    assert Item.query.count() == 0 and Image.query.count() == 0
    assert files(app) == []


def test_read_matches_search_row(ctx):
    _, c = ctx
    u = user("u", ALL)
    sid, fid = seed(u)
    h = auth(u)
    item_id = create(c, h, sid, fid, 供應商料號="S", cost="9").get_json()["data"][0]["id"]
    read = c.get(f"/product/{item_id}", headers=h).get_json()["data"]
    row = c.post("/product/search", json={"seriesId": sid}, headers=h).get_json()["data"][0]
    assert read == row
    assert read["attributes"][0] == {"fieldId": fid["供應商料號"], "fieldName": "供應商料號",
                                     "dataType": "string", "value": "S"}

    reader = user("reader", ["product.read"])
    res = c.get(f"/product/{item_id}", headers=auth(reader))
    names = [a["fieldName"] for a in res.get_json()["data"]["attributes"]]
    assert "cost" not in names


def test_read_visibility(ctx):
    _, c = ctx
    u = user("u", ALL)
    reader = user("reader", ["product.read"])
    sid, fid = seed(u)
    h, reader_h, owner = auth(u), auth(reader), u.id
    archived, deleted = [create(c, h, sid, fid, 供應商料號=n).get_json()["data"][0]["id"] for n in ("A", "B")]
    db.session.add(Archive(item_id=archived, archived_by=owner))
    db.session.get(Item, deleted).is_deleted = True
    db.session.commit()

    assert c.get(f"/product/{archived}", headers=reader_h).status_code == 404
    assert c.get(f"/product/{archived}", headers=h).get_json()["data"]["hasArchive"] is True
    assert c.get(f"/product/{deleted}", headers=h).get_json()["data"]["isDeleted"] is True
    assert c.get("/product/999", headers=h).status_code == 404


def test_edit_replaces_picture_and_removes_old_file(ctx):
    app, c = ctx
    u = user("u", ALL)
    sid, fid = seed(u)
    h = auth(u)
    item_id = create(c, h, sid, fid, 供應商料號="S", pic=png_data_url()).get_json()["data"][0]["id"]
    [old_file] = files(app)

    edit = [{"itemId": item_id, "attributes": [{"fieldId": fid["pic"], "value": png_data_url("blue")},
                                               {"fieldId": fid["price"], "value": "17.70"}]}]
    assert c.patch("/product/edit", json=edit, headers=h).status_code == 200
    values = {a["fieldName"]: a["value"] for a in c.get(f"/product/{item_id}", headers=h).get_json()["data"]["attributes"]}
    assert values["price"] == "17.70"
    assert c.get(values["pic"], headers=h).data == png("blue")
    assert old_file not in files(app) and len(files(app)) == 1

    clear = [{"itemId": item_id, "attributes": [{"fieldId": fid["pic"], "value": ""}]}]
    assert c.patch("/product/edit", json=clear, headers=h).status_code == 200
    assert files(app) == [] and Image.query.count() == 0


def test_failed_batch_edit_changes_nothing(ctx):
    """以前換圖會在中途 commit，後面的產品失敗時前面的修改已經寫入。"""
    app, c = ctx
    u = user("u", ALL)
    sid, fid = seed(u)
    h = auth(u)
    first = create(c, h, sid, fid, 供應商料號="A", pic=png_data_url()).get_json()["data"][0]["id"]
    second = create(c, h, sid, fid, 供應商料號="B").get_json()["data"][0]["id"]
    before = files(app)

    edit = [{"itemId": first, "attributes": [{"fieldId": fid["price"], "value": "5"},
                                             {"fieldId": fid["pic"], "value": png_data_url("blue")}]},
            {"itemId": second, "attributes": [{"fieldId": fid["供應商料號"], "value": "a"}]}]
    res = c.patch("/product/edit", json=edit, headers=h)
    assert res.status_code == 400 and "Duplicate values" in res.get_json()["msg"]

    db.session.expire_all()
    assert str(fid["price"]) not in db.session.get(Item, first).attributes
    assert files(app) == before


def test_edit_hidden_items_and_fields(ctx):
    _, c = ctx
    u = user("u", ALL)
    editor = user("editor", ["product.read", "product.edit"])
    sid, fid = seed(u)
    h, owner = auth(editor), u.id
    item_id = create(c, auth(u), sid, fid, 供應商料號="A").get_json()["data"][0]["id"]

    limit = [{"itemId": item_id, "attributes": [{"fieldId": fid["cost"], "value": "1"}]}]
    assert c.patch("/product/edit", json=limit, headers=h).status_code == 404

    db.session.add(Archive(item_id=item_id, archived_by=owner))
    db.session.commit()
    price = [{"itemId": item_id, "attributes": [{"fieldId": fid["price"], "value": "1"}]}]
    assert c.patch("/product/edit", json=price, headers=h).status_code == 404


def test_create_rejects_hidden_limit_fields(ctx):
    _, c = ctx
    u = user("u", ALL)
    creator = user("creator", ["product.read", "product.create"])
    sid, fid = seed(u)
    h = auth(creator)
    res = create(c, h, sid, fid, 供應商料號="A", cost="1")
    assert res.status_code == 404 and res.get_json()["msg"] == f"field_id:{fid['cost']} not found"
    # 不屬於這個 series 的欄位照舊忽略
    body = [{"seriesId": sid, "attributes": [{"fieldId": fid["供應商料號"], "value": "A"}, {"fieldId": 9999, "value": "x"}]}]
    assert c.post("/product", json=body, headers=h).status_code == 201


def test_copy(ctx):
    app, c = ctx
    u = user("u", ALL)
    reader = user("reader", ["product.read", "product.create"])
    sid, fid = seed(u)
    h, reader_h, owner = auth(u), auth(reader), u.id
    item_id = create(c, h, sid, fid, 供應商料號="S", DST料號="D", pic=png_data_url()).get_json()["data"][0]["id"]

    copy_id = c.post("/product/copy", json={"itemIds": [item_id]}, headers=h).get_json()["data"][0]["id"]
    values = {a["fieldName"]: a["value"] for a in c.get(f"/product/{copy_id}", headers=h).get_json()["data"]["attributes"]}
    assert values["供應商料號"] == "copy S" and values["DST料號"] == "D"
    assert c.get(values["pic"], headers=h).data == png() and len(files(app)) == 2

    db.session.add(Archive(item_id=item_id, archived_by=owner))
    db.session.commit()
    res = c.post("/product/copy", json={"itemIds": [item_id]}, headers=reader_h)
    assert res.status_code == 404 and res.get_json()["msg"] == f"Item(s) not found: [{item_id}]"
    assert c.post("/product/copy", json={"itemIds": []}, headers=h).status_code == 400


def test_delete_is_soft(ctx):
    _, c = ctx
    u = user("u", ALL)
    sid, fid = seed(u)
    h = auth(u)
    item_id = create(c, h, sid, fid, 供應商料號="S").get_json()["data"][0]["id"]
    assert c.delete("/product/delete", json={"itemId": [item_id]}, headers=h).status_code == 200
    assert c.get(f"/product/{item_id}", headers=h).get_json()["data"]["isDeleted"] is True


def test_unique_part_number_ignores_spaces_in_field_name(ctx):
    _, c = ctx
    u = user("u", ALL)
    h = auth(u)
    s = Series(name="spaced", created_by=u.id)
    db.session.add(s)
    db.session.flush()
    dst = Field(name="DST 料號", data_type="string", series_id=s.id, sequence=1)
    old = Field(name="DST 料號（舊）", data_type="string", series_id=s.id, sequence=2)
    db.session.add_all([dst, old])
    db.session.commit()
    sid, fid = s.id, {"DST 料號": dst.id, "old": old.id}

    def make(**values):
        return c.post("/product", json=[{"seriesId": sid, "attributes": [
            {"fieldId": fid[name], "value": value} for name, value in values.items()]}], headers=h)

    assert make(**{"DST 料號": "D-1", "old": "O-1"}).status_code == 201
    res = make(**{"DST 料號": "d-1"})
    assert res.status_code == 400 and "DST 料號 'd-1' 已存在" in res.get_json()["msg"]
    # 只有料號欄位本身，"DST 料號（舊）" 不檢查
    assert make(old="O-1").status_code == 201
