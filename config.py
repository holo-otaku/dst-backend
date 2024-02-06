import os
from datetime import timedelta


class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PORT = int(os.environ.get('PORT', 5001))
    DEBUG = bool(os.environ.get('DEBUG', True))
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'SQLALCHEMY_DATABASE_URI', 'mysql+pymysql://admin:admin@localhost:3306/db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dst-super-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=365)
    DST_MSSQL = os.environ.get(
        'DST_MSSQL', 'Driver={FreeTDS};Server=ip;port=4876;UID=sa;PWD=password;Database=db')
    IMG_PATH = os.environ.get(
        'IMG_PATH', './img')