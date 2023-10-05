from models.shared import db
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary
from datetime import datetime


class Image(db.Model):
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    # Change data type to LONGBLOB
    path = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)
