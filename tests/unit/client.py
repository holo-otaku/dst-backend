import pytest
from flask import Flask
from models.shared import db
from models import model # Import all models to ensure they are mapped
from models.user import User # Explicitly import User model

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use in-memory SQLite for testing
    db.init_app(app)
    with app.app_context():
        db.create_all() # Create tables for all models
    return app
