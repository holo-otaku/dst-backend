from models.shared import db

class ErpFieldPermission(db.Model):
    __tablename__ = 'erp_field_permission'
    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'), nullable=False)
    erp_field_name = db.Column(db.String(255), nullable=False)
    is_limit_field = db.Column(db.Boolean, default=False, nullable=False)

    series = db.relationship('Series', backref='erp_field_permissions')

    def __repr__(self):
        return f"<ErpFieldPermission {self.erp_field_name} for Series {self.series_id}>"
