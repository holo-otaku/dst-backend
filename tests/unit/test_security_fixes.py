"""Regression tests for the security-audit fixes, through the real routes and middlewares."""
import io
import zipfile
from unittest.mock import patch

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from models.shared import db
from models import model  # noqa: F401
from models.user import User, Role, Permission
from models.series import Series, Field, Item, ItemAttribute
from models.archive import Archive
from models.image import Image
from models.mapping_table import permissions_table
from routers.routes import Routes
from middlewares.middlewares import Middlewares


@pytest.fixture
def ctx(tmp_path):
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        JWT_SECRET_KEY="test-secret-key-that-is-long-enough-32b",
        IMG_PATH=str(tmp_path),
    )
    db.init_app(app)
    JWTManager(app)
    Routes(app)
    Middlewares(app)
    with app.app_context(), patch("controller.product.read_erp", return_value={}):
        db.create_all()
        for name in permissions_table:
            db.session.add(Permission(name=name))
        db.session.commit()
        yield app, app.test_client()


def user(name, perms):
    role = Role(name=f"role-{name}")
    role.permissions = Permission.query.filter(Permission.name.in_(perms)).all()
    u = User(username=name, token_version=1)
    u.set_password("pw")
    u.roles = [role]
    db.session.add(u)
    db.session.commit()
    return u


def auth(u):
    perms = [p.name for r in u.roles for p in r.permissions]
    token = create_access_token(identity=str(u.id), additional_claims={
        "permissions": perms, "tokenVersion": u.token_version})
    return {"Authorization": f"Bearer {token}"}


def catalog(owner, limit_picture=False):
    s = Series(name="S", created_by=owner.id)
    db.session.add(s)
    db.session.flush()
    name = Field(name="name", data_type="string", series_id=s.id)
    cost = Field(name="cost", data_type="number", series_id=s.id, is_limit_field=True)
    pic = Field(name="pic", data_type="picture", series_id=s.id, is_limit_field=limit_picture)
    db.session.add_all([name, cost, pic])
    db.session.flush()
    item = Item(series_id=s.id)
    db.session.add(item)
    db.session.flush()
    db.session.add_all([ItemAttribute(item_id=item.id, field_id=name.id, value="=1+1"),
                        ItemAttribute(item_id=item.id, field_id=cost.id, value="123")])
    db.session.commit()
    return s, name, cost, pic, item


def test_refresh_rejects_revoked_token(ctx):
    _, c = ctx
    u = user("u", ["role.read"])
    old = auth(u)
    u.token_version += 1
    db.session.commit()
    assert c.post("/jwt/refresh", headers=old).status_code == 401


def test_user_logs_need_log_read(ctx):
    _, c = ctx
    u = user("u", [])
    assert c.get(f"/log/user/{u.id}", headers=auth(u)).status_code == 403


def test_no_privilege_escalation(ctx):
    _, c = ctx
    admin_role = Role(name="admin", permissions=Permission.query.all())
    db.session.add(admin_role)
    db.session.commit()
    acct = user("acct", ["user.read", "user.edit"])
    rolemgr = user("rolemgr", ["role.read", "role.edit"])
    acct_id, acct_h, admin_id = acct.id, auth(acct), admin_role.id
    own_role, rolemgr_h = rolemgr.roles[0].id, auth(rolemgr)
    body = {"roleName": "x", "permissionIds": [p.id for p in Permission.query.all()]}
    assert c.patch(f"/user/{acct_id}", json={"roleId": admin_id}, headers=acct_h).status_code == 403
    assert c.patch(f"/role/{own_role}", json=body, headers=rolemgr_h).status_code == 403


def test_password_change_and_role_delete_revoke_tokens(ctx):
    _, c = ctx
    admin = user("admin", permissions_table)
    victim = user("victim", ["role.read"])
    h, vid, role_id = auth(admin), victim.id, victim.roles[0].id
    c.patch(f"/user/{vid}", json={"password": "new"}, headers=h)
    assert db.session.get(User, vid).token_version == 2
    c.delete(f"/role/{role_id}", headers=h)
    assert db.session.get(User, vid).token_version == 3


def test_login_does_not_reveal_existing_users(ctx):
    _, c = ctx
    user("alice", [])
    assert c.post("/login", json={"username": "alice"}).status_code == 401
    assert c.post("/login", json={"username": "alice", "password": 5}).status_code == 401


def test_limit_field_not_searchable_or_filterable(ctx):
    _, c = ctx
    low = user("low", ["product.read", "product.create"])
    s, _, cost, _, _ = catalog(low)
    h, sid, cid = auth(low), s.id, cost.id
    assert c.get(f"/field/search?field_id={cid}", headers=h).get_json()["code"] == 403
    body = {"seriesId": sid, "filters": [{"fieldId": cid, "value": 100, "operation": "greater"}]}
    assert c.post("/product/search", json=body, headers=h).status_code != 200
    assert c.post(f"/product/search?sort={cid},asc", json={"seriesId": sid}, headers=h).status_code != 200


def test_edit_cannot_soft_delete_without_product_delete(ctx):
    _, c = ctx
    editor = user("editor", ["product.read", "product.edit"])
    _, _, _, _, item = catalog(editor)
    iid = item.id
    res = c.patch("/product/edit", json=[{"itemId": iid, "attributes": [], "isDeleted": 1}], headers=auth(editor))
    assert res.status_code == 403
    assert db.session.get(Item, iid).is_deleted is False


def test_export_writes_formulas_as_text(ctx):
    _, c = ctx
    reader = user("reader", ["product.read"])
    s, *_ = catalog(reader)
    res = c.post("/product/export", json={"seriesId": s.id, "filters": []}, headers=auth(reader))
    sheet = zipfile.ZipFile(io.BytesIO(res.data)).read("xl/worksheets/sheet1.xml").decode()
    assert "<f>" not in sheet


def test_image_needs_product_read_and_limit_permission(ctx):
    app, c = ctx
    nobody = user("nobody", [])
    reader = user("reader", ["product.read"])
    _, _, _, pic, item = catalog(reader, limit_picture=True)
    path = f"{app.config['IMG_PATH']}/x.png"
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n")
    image = Image(name="x", path=path)
    db.session.add(image)
    db.session.flush()
    db.session.add(ItemAttribute(item_id=item.id, field_id=pic.id, value=str(image.id)))
    db.session.commit()
    assert c.get(f"/image/{image.id}", headers=auth(nobody)).status_code == 403
    assert c.get(f"/image/{image.id}", headers=auth(reader)).status_code == 403


def test_archived_and_deleted_series_items_hidden(ctx):
    _, c = ctx
    reader = user("reader", ["product.read", "product.create"])
    s, _, _, _, item = catalog(reader)
    db.session.add(Archive(item_id=item.id, archived_by=reader.id))
    db.session.commit()
    h = auth(reader)
    assert c.get(f"/product/{item.id}", headers=h).status_code == 404
    assert c.post("/product/copy", json={"itemIds": [item.id]}, headers=h).status_code == 404
    res = c.post("/product/search?limit=0", json={"seriesId": s.id, "isArchived": 1}, headers=h)
    assert res.get_json()["totalCount"] == 0

    db.session.query(Archive).delete()
    db.session.get(Series, s.id).status = 0
    db.session.commit()
    assert c.get(f"/product/{item.id}", headers=h).status_code == 404
