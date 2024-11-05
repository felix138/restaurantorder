from app import db
from datetime import datetime

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    member_level = db.Column(db.Integer, default=1)
    points = db.Column(db.Integer, default=0)
    total_consumption = db.Column(db.DECIMAL(10,2), default=0)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    
    # 关联
    user = db.relationship('User', backref='customer_info', lazy=True)