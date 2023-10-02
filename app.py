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
from middlewares.middlewares import Middlewares

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

Routes(app)
Logger(app)
CORS(app)
Middlewares(app)

if __name__ == '__main__':

    with app.app_context():
        create_default_permissions()
        create_admin_role()
        create_admin_user()

    app.run(host='0.0.0.0', debug=True, port=app.config['PORT'])
