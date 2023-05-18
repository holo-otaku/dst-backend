from models.shared import db
from sqlalchemy import Column, Integer, String, Boolean


class Item(db.Model):
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True)
    type_id = Column(Integer)
    name = Column(String)


class attributes(db.Model):
    __tablename__ = 'attributes'
    id = Column(Integer, primary_key=True)
    type_id = Column(Integer)
    name = Column(String)
    type = Column(String)
    is_requirement = Column(Boolean)
    is_filter = Column(Boolean)


class ItemAttribute(db.Model):
    __tablename__ = 'item_attributes'
    item_id = Column(Integer, primary_key=True)
    attribute_id = Column(Integer)
    value = Column(String)


class Type(db.Model):
    __tablename__ = 'type'
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
