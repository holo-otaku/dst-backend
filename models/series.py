from models.shared import db
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship


class Series(db.Model):
    __tablename__ = 'series'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)
    status = Column(Integer, default=1)

    creator = relationship('User')
    fields = relationship('Field', back_populates='series')


class Field(db.Model):
    __tablename__ = 'field'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    data_type = Column(String(50), nullable=False)
    is_required = Column(Boolean, default=0, nullable=False)
    is_filtered = Column(Boolean, default=0, nullable=False)
    is_erp = Column(Boolean, default=0, nullable=False)
    series_id = Column(Integer, ForeignKey('series.id'))

    series = relationship('Series', back_populates='fields')
    item_attribute = relationship('ItemAttribute', back_populates='field')

class Item(db.Model):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey('series.id'))
    name = Column(String(length=50))
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)

    attributes = relationship('ItemAttribute', back_populates='item')
    series = relationship('Series')


class ItemAttribute(db.Model):
    __tablename__ = 'item_attribute'

    item_id = Column(Integer, ForeignKey('item.id'), primary_key=True)
    field_id = Column(Integer, ForeignKey('field.id'), primary_key=True)
    value = Column(String(length=256))

    item = relationship('Item')
    field = relationship('Field', back_populates='item_attribute')
