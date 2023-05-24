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

    creator = relationship('User', backref='series')


class Field(db.Model):
    __tablename__ = 'fields'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    data_type = Column(String(50), nullable=False)
    is_required = Column(Boolean, default=0)
    series_id = Column(Integer, ForeignKey('series.id'))

    series = relationship('Series', backref='fields')
