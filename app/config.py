import os
from datetime import timedelta

class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))
    BASE_DIR = basedir
    DEBUG = True
    SECRET_KEY = 'mysecretkey'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + \
        os.path.join(basedir, 'database.db')
    SQLALCHEMY_BINDS = {
        'mssql': 'mssql+pyodbc://sa:1QAZ2wsx3edc@localhost:5434/MIS2000?driver=ODBC+Driver+17+for+SQL+Server'
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'dst-super-secret'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)