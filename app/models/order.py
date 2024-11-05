from app import db
from datetime import datetime
from app.config import Config
import json

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    table_number = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='pending')
    payment_status = db.Column(db.String(20), default='unpaid')
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    actual_amount = db.Column(db.Numeric(10, 2), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 收银机相关字段（仅当启用收银机接口时使用）
    if Config.POS_ENABLED:
        pos_serial = db.Column(db.String(50))
        pos_status = db.Column(db.String(20))
        payment_method = db.Column(db.String(20))
        payment_time = db.Column(db.DateTime)
    
    # 关联
    items = db.relationship('OrderItem', backref='order', lazy=True)
    staff = db.relationship('Staff', backref='orders', lazy=True)

    def to_pos_format(self):
        """转换为收银机可识别的格式（仅当启用收银机接口时可用）"""
        if not Config.POS_ENABLED:
            return None
            
        pos_data = {
            "orderNo": self.order_number,
            "tableNo": self.table_number,
            "amount": float(self.total_amount),
            "items": [
                {
                    "name": item.item.name if item.item_type == 'item' else item.set_meal.name,
                    "quantity": item.quantity,
                    "price": float(item.original_price),
                    "subtotal": float(item.original_price * item.quantity)
                }
                for item in self.items
            ]
        }
        return json.dumps(pos_data, ensure_ascii=False)

    def update_from_pos(self, pos_data):
        """从收银机更新订单状态（仅当启用收银机接口时可用）"""
        if not Config.POS_ENABLED:
            return False
            
        self.pos_serial = pos_data.get('serialNo')
        self.pos_status = pos_data.get('status')
        self.payment_method = pos_data.get('paymentMethod')
        self.payment_time = datetime.now()
        if pos_data.get('status') == 'paid':
            self.payment_status = 'paid'
            self.status = 'completed'
        return True

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'))
    set_meal_id = db.Column(db.Integer, db.ForeignKey('set_meals.id'))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    original_price = db.Column(db.Numeric(10, 2), nullable=False)
    actual_price = db.Column(db.Numeric(10, 2), nullable=False)
    item_type = db.Column(db.String(20), nullable=False)  # 'item' or 'set_meal'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 添加关联关系
    item = db.relationship('Item', backref='order_items', lazy=True)
    set_meal = db.relationship('SetMeal', backref='order_items', lazy=True)