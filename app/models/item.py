from models.shared import db
from sqlalchemy import Column, Integer, String


class Item(db.Model):
    __bind_key__ = 'main'
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True)
    type_id = Column(Integer)
    name = Column(String)
