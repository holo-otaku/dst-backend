from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.mysql import JSON

from models.shared import db


class ActivityLog(db.Model):
    __tablename__ = 'activity_log'

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer)
    url = db.Column(Text)
    payload = db.Column(JSON)  # 使用 JSON 型別來保存 payload
    method = db.Column(db.String(10))
    created_at = Column(DateTime, default=datetime.now)
