from routers.user import user


class routes:
    def __init__(self, app) -> None:
        app.register_blueprint(user)
