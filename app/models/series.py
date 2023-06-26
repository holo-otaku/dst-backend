from models.shared import db
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship


class Series(db.Model):
    __tablename__ = 'series'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now)

    creator = relationship('User')
    fields = relationship('Field')


class Field(db.Model):
    __tablename__ = 'field'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    data_type = Column(String(50), nullable=False)
    is_required = Column(Boolean, default=0)
    is_filtered = Column(Boolean)
    series_id = Column(Integer, ForeignKey('series.id'))

    item_attributes = relationship('ItemAttribute')


class Item(db.Model):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey('series.id'))
    name = Column(String(length=50))

    series = relationship('Series')


class ItemAttribute(db.Model):
    __tablename__ = 'item_attribute'

    item_id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    field_id = Column(Integer, ForeignKey('field.id'), primary_key=True)
    value = Column(String(length=50))

    item = relationship('Item')
