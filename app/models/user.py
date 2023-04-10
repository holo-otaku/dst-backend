from models.shared import db
from sqlalchemy import Column, Integer, String


class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), index=True)
    age = Column(Integer)
