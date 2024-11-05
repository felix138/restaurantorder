from app import db
from datetime import datetime

class SetMeal(db.Model):
    __tablename__ = 'set_meals'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    member_price = db.Column(db.Numeric(10, 2))
    description = db.Column(db.Text)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # 添加关系
    items = db.relationship('SetMealItem', backref='set_meal', lazy=True)

class SetMealItem(db.Model):
    __tablename__ = 'set_meal_items'
    
    id = db.Column(db.Integer, primary_key=True)
    set_meal_id = db.Column(db.Integer, db.ForeignKey('set_meals.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
    # 添加关系
    item = db.relationship('Item', backref='set_meal_items', lazy=True)