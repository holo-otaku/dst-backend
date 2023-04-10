from models.shared import db
from sqlalchemy import Column, Integer, String


class Type(db.Model):
    __tablename__ = 'type'
    id = Column(Integer, primary_key=True)
    name = Column(String(64))