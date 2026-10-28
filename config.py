import os
from dotenv import load_dotenv
from datetime import timedelta


load_dotenv()


class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PORT = int(os.environ.get('PORT', 5001))
    DEBUG = os.environ.get('DEBUG', 'false').lower() in ('1', 'true')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'SQLALCHEMY_DATABASE_URI', 'mysql+pymysql://admin:admin@localhost:3306/db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 沒設定就啟動失敗：寫死的預設值任何人都能拿來偽造 admin token
    JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=365)
    DST_MSSQL = os.environ.get(
        'DST_MSSQL', 'Driver={FreeTDS};Server=ip;port=4876;UID=sa;PWD=password;Database=db')
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 單一請求上限（含 base64 圖片）
    IMG_PATH = os.environ.get(
        'IMG_PATH', './img')