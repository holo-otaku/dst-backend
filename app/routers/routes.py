from routers.user import user
from routers.jwt import jwt


class routes:
    def __init__(self, app) -> None:
        app.register_blueprint(user)
        app.register_blueprint(jwt)
