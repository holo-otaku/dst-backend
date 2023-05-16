from flask import Flask

from models.shared import db
from models import model
from routers.routes import routes
from logs.logger import logger
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

routes(app)
logger(app)

if __name__ == '__main__':

    app.run(host='0.0.0.0', debug=True, port=5001)
