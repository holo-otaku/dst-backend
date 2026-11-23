from datetime import datetime
from sqlalchemy import JSON, DateTime, Integer, String, Text

from models.shared import db


class ActivityLog(db.Model):
    __tablename__ = 'activity_log'

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, index=True)  # Added index for user_id
    url = db.Column(Text)
    payload = db.Column(JSON)  # 使用 JSON 型別來保存 payload
    method = db.Column(db.String(10))
    created_at = db.Column(DateTime, default=datetime.now, index=True)
    status = db.Column(Integer)  # HTTP 狀態碼，401/403 代表被擋下
    ip = db.Column(String(45))
    user_agent = db.Column(String(255))
