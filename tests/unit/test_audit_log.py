"""操作紀錄要能回答：誰、從哪、做了什麼、有沒有被擋下。"""
from models.log import ActivityLog
from tests.unit.test_security_fixes import ctx, user, auth  # noqa: F401


def logs():
    return ActivityLog.query.order_by(ActivityLog.id).all()


def test_login_attempts_are_logged_without_password(ctx):
    app, client = ctx
    alice_id = user("alice", []).id

    headers = {"User-Agent": "test-browser", "X-Forwarded-For": "203.0.113.9"}
    client.post("/login", json={"username": "alice", "password": "wrong"}, headers=headers)
    client.post("/login", json={"username": "alice", "password": "pw"}, headers=headers)
    client.post("/login", json={"username": "nobody", "password": "x"})

    failed, ok, unknown = logs()
    assert (failed.user_id, failed.status) == (alice_id, 401)
    assert (ok.user_id, ok.status) == (alice_id, 200)
    assert (unknown.user_id, unknown.status, unknown.payload["username"]) == (None, 401, "nobody")
    assert failed.payload == {"username": "alice", "password": "***"}
    assert failed.user_agent == "test-browser"


def test_user_and_role_changes_are_logged_with_password_redacted(ctx):
    app, client = ctx
    admin = user("admin", ["user.create", "user.edit", "role.edit"])
    headers = auth(admin)
    admin_id = admin.id
    role_id = admin.roles[0].id

    client.post("/user", json={"username": "bob", "password": "secret", "roleId": role_id}, headers=headers)

    (row,) = logs()
    assert (row.user_id, row.url, row.method, row.status) == (admin_id, "/user", "POST", 201)
    assert row.payload == {"username": "bob", "password": "***", "roleId": role_id}
    assert row.ip


def test_denied_and_bad_token_requests_are_logged(ctx):
    app, client = ctx
    viewer = user("viewer", [])
    headers = auth(viewer)
    viewer_id = viewer.id

    client.post("/role", json={"name": "x", "permissionIds": []}, headers=headers)
    client.get("/series", headers={"Authorization": "Bearer forged"})

    denied, forged = logs()
    assert (denied.user_id, denied.url, denied.status) == (viewer_id, "/role", 403)
    assert (forged.user_id, forged.status) == (None, 401)


def test_noise_is_not_logged(ctx):
    app, client = ctx
    client.get("/health")
    client.get("/wp-login.php")
    client.options("/series")
    assert logs() == []
