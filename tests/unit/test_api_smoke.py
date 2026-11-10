"""每支 API 的成功路徑都走一次真的路由與資料庫（CI 也會用 PG 跑），確認 API 能正常運作。

錯誤路徑與權限檢查在其他測試檔；ERP 連的是外部 MSSQL，這裡由 ctx fixture mock 掉。
"""
import base64
import io

from PIL import Image as PILImage

from models.mapping_table import permissions_table
from models.series import Item
from models.shared import db
from models.user import Permission, User
from tests.unit.test_security_fixes import ctx, user  # noqa: F401


def png(color="red"):
    buffer = io.BytesIO()
    PILImage.new("RGB", (4, 4), color).save(buffer, "PNG")
    return buffer.getvalue()


def png_data_url(color="red"):
    return "data:image/png;base64," + base64.b64encode(png(color)).decode()


def login(c, username="root", password="pw"):
    res = c.post("/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.get_json()
    return {"Authorization": f"Bearer {res.get_json()['data']['accessToken']}"}


def ok(res, status=200):
    assert res.status_code == status, (res.status_code, res.get_data(as_text=True)[:300])
    return res.get_json()


def test_health_login_refresh(ctx):
    _, c = ctx
    user("root", permissions_table)
    ok(c.get("/health"))
    h = login(c)
    token = ok(c.post("/jwt/refresh", headers=h))["accessToken"]
    ok(c.get("/series", headers={"Authorization": f"Bearer {token}"}))


def test_series_product_image_archive_flow(ctx):
    _, c = ctx
    user("root", permissions_table)
    h = login(c)

    fields = [
        {"name": "供應商料號", "dataType": "string", "isRequired": True},
        {"name": "DST料號", "dataType": "string", "searchErp": True},
        {"name": "price", "dataType": "number", "isFiltered": True},
        {"name": "day", "dataType": "datetime"},
        {"name": "flag", "dataType": "boolean"},
        {"name": "pic", "dataType": "picture"},
    ]
    sid = ok(c.post("/series", json={"name": "Smoke", "fields": fields}, headers=h), 201)["data"]["id"]
    assert [s["id"] for s in ok(c.get("/series?showField=1", headers=h))["data"]] == [sid]
    fid = {f["name"]: f["id"] for f in ok(c.get(f"/series/{sid}", headers=h))["data"]["fields"]}

    def attrs(supplier, dst, price, day, flag):
        return [{"fieldId": fid["供應商料號"], "value": supplier}, {"fieldId": fid["DST料號"], "value": dst},
                {"fieldId": fid["price"], "value": price}, {"fieldId": fid["day"], "value": day},
                {"fieldId": fid["flag"], "value": flag}]

    body = [{"seriesId": sid, "attributes": attrs("S-1", "D-1", "17.70", "2025-03-01", True)
             + [{"fieldId": fid["pic"], "value": png_data_url()}]},
            {"seriesId": sid, "attributes": attrs("S-2", "D-2", "5", "2025/01/01", False)}]
    first, second = [row["id"] for row in ok(c.post("/product", json=body, headers=h), 201)["data"]]

    product = ok(c.get(f"/product/{first}", headers=h))["data"]
    values = {a["fieldName"]: a["value"] for a in product["attributes"]}
    assert values["price"] == "17.70" and values["day"] == "2025/03/01" and values["flag"] is True
    image = c.get(values["pic"], headers=h)
    assert image.status_code == 200 and image.data == png()

    edit = [{"itemId": second, "attributes": [{"fieldId": fid["price"], "value": "25"},
                                              {"fieldId": fid["pic"], "value": png_data_url("blue")}]}]
    ok(c.patch("/product/edit", json=edit, headers=h))

    def search(filters, query=""):
        return ok(c.post(f"/product/search{query}", json={"seriesId": sid, "filters": filters}, headers=h))

    assert [r["itemId"] for r in search([], f"?sort={fid['price']},desc")["data"]] == [second, first]
    assert search([{"fieldId": fid["flag"], "value": False}])["totalCount"] == 1
    assert search([{"fieldId": fid["day"], "value": "2025/02/01", "operation": "greater"}])["totalCount"] == 1
    assert search([{"fieldId": fid["DST料號"], "value": "d-"}])["totalCount"] == 2
    assert ok(c.get(f"/field/search?field_id={fid['供應商料號']}&search_value=s", headers=h))["data"] == ["S-1", "S-2"]

    export = c.post("/product/export", json={"seriesId": sid}, headers=h)
    assert export.status_code == 200 and export.mimetype.endswith("spreadsheetml.sheet")

    copy = ok(c.post("/product/copy", json={"itemIds": [first]}, headers=h), 201)["data"][0]["id"]
    copied = {a["fieldName"]: a["value"] for a in ok(c.get(f"/product/{copy}", headers=h))["data"]["attributes"]}
    assert copied["供應商料號"] == "copy S-1" and copied["pic"] != values["pic"]

    ok(c.post("/archive", json={"itemIds": [copy]}, headers=h))
    assert ok(c.post("/product/search", json={"seriesId": sid, "isArchived": 1}, headers=h))["totalCount"] == 1
    ok(c.delete("/archive", json={"itemIds": [copy]}, headers=h))

    ok(c.delete("/product/delete", json={"itemId": [copy]}, headers=h))
    assert ok(c.post("/product/search", json={"seriesId": sid, "isDeleted": 1}, headers=h))["totalCount"] == 1

    update = {"name": "Smoke 2", "create": [{"name": "note", "dataType": "string", "sequence": 9}],
              "delete": [fid["pic"]]}
    ok(c.patch(f"/series/{sid}", json=update, headers=h))
    db.session.expire_all()
    assert all(str(fid["pic"]) not in item.attributes for item in Item.query.all())

    ok(c.delete(f"/series/{sid}", headers=h))
    assert c.get(f"/series/{sid}", headers=h).status_code == 404


def test_image_upload(ctx):
    _, c = ctx
    user("root", permissions_table)
    h = login(c)
    res = c.post("/image", data={"image_data": (io.BytesIO(png()), "a.png")}, headers=h,
                 content_type="multipart/form-data")
    image_id = ok(res, 201)["image_id"]
    assert c.get(f"/image/{image_id}", headers=h).data == png()


def test_permission_role_user_and_logs(ctx):
    _, c = ctx
    root_id = user("root", permissions_table).id
    h = login(c)

    assert ok(c.get("/permission?limit=100", headers=h))["totalCount"] == len(permissions_table)
    perm_id = ok(c.post("/permission", json={"name": "smoke.read"}, headers=h))["data"]["id"]
    assert ok(c.get(f"/permission/{perm_id}", headers=h))["data"]["name"] == "smoke.read"
    # 只能改名/刪除自己持有的權限：直接在 DB 授權，重新登入讓 token 帶上它
    # （controller 結束會關掉 session，之前拿到的物件已經 detached，要重新查）
    root_role = db.session.get(User, root_id).roles[0]
    root_role.permissions.append(db.session.get(Permission, perm_id))
    db.session.commit()
    h = login(c)
    ok(c.patch(f"/permission/{perm_id}", json={"name": "smoke.write"}, headers=h))
    # 改名、刪除都會讓持有者的 token 失效
    assert c.get("/permission", headers=h).status_code == 401
    h = login(c)
    ok(c.delete(f"/permission/{perm_id}", headers=h))
    h = login(c)

    read_id = Permission.query.filter_by(name="product.read").one().id
    role_id = ok(c.post("/role", json={"roleName": "viewer", "permissionIds": [read_id]}, headers=h), 201)["data"]["id"]
    assert "viewer" in [r["name"] for r in ok(c.get("/role", headers=h))["data"]]
    ok(c.get(f"/role/{role_id}", headers=h))
    ok(c.patch(f"/role/{role_id}", json={"roleName": "viewer2", "permissionIds": [read_id]}, headers=h))

    new_user = {"username": "alice", "password": "pw1", "roleId": role_id}
    alice_id = ok(c.post("/user", json=new_user, headers=h), 201)["data"]["id"]
    assert "alice" in [u["userName"] for u in ok(c.get("/user?all=true", headers=h))["data"]]
    ok(c.get(f"/user/{alice_id}", headers=h))
    ok(c.patch(f"/user/{alice_id}", json={"password": "pw2"}, headers=h))
    alice = login(c, "alice", "pw2")
    ok(c.post(f"/user/{alice_id}/force-logout", headers=h))
    assert c.post("/product/search", json={"seriesId": 1}, headers=alice).status_code == 401
    ok(c.delete(f"/user/{alice_id}", headers=h))
    assert c.post("/login", json={"username": "alice", "password": "pw2"}).status_code == 403
    ok(c.delete(f"/role/{role_id}", headers=h))

    assert ok(c.get("/log", headers=h))["totalCount"] > 0
    assert ok(c.get(f"/log/user/{root_id}", headers=h))["data"]

    ok(c.post("/user/force-logout-all", headers=h))
    assert c.get("/log", headers=h).status_code == 401
    assert db.session.get(User, root_id).token_version > 1
