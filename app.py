from flask import Flask, jsonify
from models.shared import db
from models import model
from routers.routes import Routes
from modules.logger import Logger
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from controller.user import create_admin_user
from controller.role import create_admin_role
from controller.permission import create_default_permissions
from middlewares.middlewares import Middlewares

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)


# /jwt/refresh 不經過 TokenVersionMiddleware，token 無效時也要讓前端強制登出
@jwt.invalid_token_loader
def invalid_token_callback(reason):
    return jsonify({"code": 401, "msg": reason, "forceLogout": True}), 401


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"code": 401, "msg": "Token has expired", "forceLogout": True}), 401


Routes(app)
Logger(app)
CORS(app)
Middlewares(app)

if __name__ == '__main__':

    with app.app_context():
        create_default_permissions()
        create_admin_role()
        create_admin_user()

    app.run(host='0.0.0.0', debug=app.config['DEBUG'], port=app.config['PORT'])
