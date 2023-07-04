from flask import Flask

from models.shared import db
from models import model
from routers.routes import routes
from modules.logger import logger
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from controller.user import create_default_admin

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

routes(app)
logger(app)

if __name__ == '__main__':
    # 檢查是否已經執行過 create_default_admin()
    if not app.config.get('DEFAULT_ADMIN_CREATED'):
        with app.app_context():
            create_default_admin()

        # 設置標誌位，表示已經執行過 create_default_admin()
        app.config['DEFAULT_ADMIN_CREATED'] = True

    app.run(host='0.0.0.0', debug=True, port=5001)
