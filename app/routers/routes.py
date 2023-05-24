from routers.user import user
from routers.role import role
from routers.permission import permission
from routers.series import series
from routers.jwt import jwt


class routes:
    def __init__(self, app) -> None:
        app.register_blueprint(user, url_prefix='/users')
        app.register_blueprint(role, url_prefix='/roles')
        app.register_blueprint(permission, url_prefix='/permissions')
        app.register_blueprint(series, url_prefix='/series')
        app.register_blueprint(jwt)
