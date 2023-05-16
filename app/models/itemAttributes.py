from models.shared import db
from sqlalchemy import Column, Integer, String


class ItemAttribute(db.Model):
    __bind_key__ = 'main'
    __tablename__ = 'item_attributes'
    item_id = Column(Integer, primary_key=True)
    attribute_id = Column(Integer)
    value = Column(String)
