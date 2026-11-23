from routers.user import user
from routers.role import role
from routers.permission import permission
from routers.series import series
from routers.product import products
from routers.jwt import jwt
from routers.swagger import create_api
from routers.healthcheck import health_check
from routers.image import image
from routers.log import log
from routers.archive import archive
from routers.field import field


class Routes:
    def __init__(self, app) -> None:
        api = create_api(app)
        api.register_blueprint(user, url_prefix='/user')
        api.register_blueprint(role, url_prefix='/role')
        api.register_blueprint(permission, url_prefix='/permission')
        api.register_blueprint(series, url_prefix='/series')
        api.register_blueprint(products, url_prefix='/product')
        api.register_blueprint(jwt)
        api.register_blueprint(health_check, url_prefix='/health')
        api.register_blueprint(image, url_prefix='/image')
        api.register_blueprint(log, url_prefix='/log')
        api.register_blueprint(archive, url_prefix='/archive')
        api.register_blueprint(field, url_prefix='/field')
