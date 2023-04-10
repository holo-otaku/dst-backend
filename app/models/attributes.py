from models.shared import db
from sqlalchemy import Column, Integer, String, Boolean


class attributes(db.Model):
    __tablename__ = 'attributes'
    id = Column(Integer, primary_key=True)
    type_id = Column(Integer)
    name = Column(String)
    type = Column(String)
    is_requirement = Column(Boolean)
    is_filter = Column(Boolean)