from app import db
from datetime import datetime
from sqlalchemy import DECIMAL

class Item(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    price = db.Column(DECIMAL(10,2), nullable=False)
    member_price = db.Column(DECIMAL(10,2))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    stock_quantity = db.Column(db.Integer, default=-1)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.TIMESTAMP, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    category = db.relationship('Category', backref='items', lazy=True)