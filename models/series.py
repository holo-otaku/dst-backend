from models.shared import db
from datetime import datetime
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship


class Series(db.Model):
    __tablename__ = 'series'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
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
    search_erp = Column(Boolean, default=0, nullable=False)
    is_limit_field = Column(Boolean, default=0, nullable=False)
    series_id = Column(Integer, ForeignKey('series.id'))
    sequence = Column(Integer, nullable=False, default=0)

    series = relationship('Series', back_populates='fields')


class Item(db.Model):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey('series.id'))
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)
    is_deleted = Column(Boolean, default=0, nullable=False)
    # {str(field_id): 值}，值的型別規則見 controller/field_value.py；沒有值的欄位不放 key
    attributes = Column(
        MutableDict.as_mutable(JSON().with_variant(JSONB(), "postgresql")),
        nullable=False, default=dict, server_default="{}",
    )

    series = relationship('Series')
