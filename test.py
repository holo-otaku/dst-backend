from flask import Flask

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


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1qaz%40WSX3edc@localhost:3306/test'
    db.init_app(app)
    migrate = Migrate(app, db)
    jwt = JWTManager(app)

    Routes(app)
    Logger(app)
    CORS(app)

    return app, db


if __name__ == '__main__':
    app, db = create_app()

    with app.app_context():
        create_default_permissions()
        create_admin_role()
        create_admin_user()

    app.run(host='0.0.0.0', debug=True, port=5001)
