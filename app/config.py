import os


class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))
    BASE_DIR = basedir
    DEBUG = True
    SECRET_KEY = 'mysecretkey'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + \
        os.path.join(basedir, 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
