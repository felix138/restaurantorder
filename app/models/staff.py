from app import db
from datetime import datetime

class Staff(db.Model):
    __tablename__ = 'staff'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employee_id = db.Column(db.String(50), unique=True)
    department = db.Column(db.String(50))
    position = db.Column(db.String(50))
    hire_date = db.Column(db.Date)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    # 关联
    user = db.relationship('User', backref='staff_info', lazy=True) 