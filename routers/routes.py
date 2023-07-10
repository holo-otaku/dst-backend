from routers.user import user
from routers.role import role
from routers.permission import permission
from routers.series import series
from routers.product import products
from routers.jwt import jwt
from routers.swagger import swagger_ui_blueprint
from routers.healthcheck import health_check


class routes:
    def __init__(self, app) -> None:
        app.register_blueprint(swagger_ui_blueprint)
        app.register_blueprint(user, url_prefix='/user')
        app.register_blueprint(role, url_prefix='/role')
        app.register_blueprint(permission, url_prefix='/permission')
        app.register_blueprint(series, url_prefix='/series')
        app.register_blueprint(products, url_prefix='/product')
        app.register_blueprint(jwt)
        app.register_blueprint(health_check, url_prefix='/health')
