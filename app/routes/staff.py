from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models.category import Category
from app.models.item import Item
from app.models.set_meal import SetMeal, SetMealItem
from app.models.order import Order, OrderItem
from app.models.staff import Staff
from app import db
from datetime import datetime
import logging
from sqlalchemy.orm import joinedload

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

bp = Blueprint('staff', __name__, url_prefix='/staff')

@bp.route('/')
@login_required
def index():
    if current_user.role_id != 3:  # 确保是员工角色
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    return render_template('staff/index.html')

@bp.route('/take_order')
@login_required
def take_order():
    if current_user.role_id != 3:  # 确保是员工角色
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    try:
        logger.debug("开始加载点餐页面")
        
        # 获取分类和菜品
        categories = Category.query.order_by(Category.sort_order).all()
        logger.debug(f"找到 {len(categories)} 个分类")
        
        items = Item.query.filter_by(is_available=True).all()
        logger.debug(f"找到 {len(items)} 个可用菜品")
        
        # 获取套餐数据
        logger.debug("开始查询套餐数据")
        set_meals = SetMeal.query.filter_by(is_available=True)\
                                .options(joinedload(SetMeal.items).joinedload(SetMealItem.item))\
                                .all()
        logger.debug(f"找到 {len(set_meals)} 个可用套餐")
        
        set_meal_details = {}
        for set_meal in set_meals:
            logger.debug(f"处理套餐: {set_meal.id} - {set_meal.name}")
            
            items_list = []
            for smi in set_meal.items:
                if smi.item and smi.item.is_available:
                    logger.debug(f"添加菜品到套餐: {smi.item.name} x {smi.quantity}")
                    items_list.append({
                        'id': smi.item.id,
                        'name': smi.item.name,
                        'quantity': smi.quantity,
                        'price': float(smi.item.price)
                    })
            
            set_meal_details[set_meal.id] = {
                'id': set_meal.id,
                'name': set_meal.name,
                'price': float(set_meal.price),
                'member_price': float(set_meal.member_price) if set_meal.member_price else None,
                'description': set_meal.description,
                'items': items_list
            }
            
            logger.debug(f"套餐 {set_meal.id} 详情: {set_meal_details[set_meal.id]}")
        
        logger.debug("点餐页面数据准备完成")
        
        # 直接传递原始的 set_meals 对象和处理后的 set_meal_details
        return render_template('order/menu.html',
                             categories=categories,
                             items=items,
                             set_meals=set_meals,
                             set_meal_details=set_meal_details)
                             
    except Exception as e:
        logger.error(f"加载点餐页面失败: {str(e)}", exc_info=True)
        flash('加载点餐页面失败：' + str(e))
        return redirect(url_for('staff.index'))

@bp.route('/submit_order', methods=['POST'])
@login_required
def submit_order():
    if current_user.role_id != 3:
        return jsonify({'success': False, 'message': '没有权限执行此操作'}), 403
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        # 获取员工信息
        staff = Staff.query.filter_by(user_id=current_user.id).first()
        if not staff:
            return jsonify({'success': False, 'message': '未找到员工信息'}), 404
        
        # 创建订单
        order = Order()
        order.order_number = datetime.now().strftime('%Y%m%d%H%M%S')
        order.table_number = data.get('table_number')
        order.staff_id = staff.id
        order.status = 'pending'
        order.payment_status = 'unpaid'
        
        # 计算订单总金额
        total_amount = 0
        for item_data in data.get('items', []):
            quantity = item_data.get('quantity', 1)
            price = float(item_data['price'])
            total_amount += price * quantity
            
            # 创建订单项
            order_item = OrderItem()
            if item_data['type'] == 'item':
                order_item.item_id = item_data['id']
            else:
                order_item.set_meal_id = item_data['id']
            
            order_item.quantity = quantity
            order_item.original_price = price
            order_item.actual_price = price
            order_item.item_type = item_data['type']
            
            order.items.append(order_item)
        
        order.total_amount = total_amount
        order.actual_amount = total_amount
        
        # 保存到数据库
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '订单提交成功',
            'order_id': order.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"订单提交失败: {str(e)}")  # 添加错误日志
        return jsonify({
            'success': False,
            'message': f'订单提交失败: {str(e)}'
        }), 500

@bp.route('/menu')
@login_required
def menu():
    if current_user.role_id != 3:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    categories = Category.query.order_by(Category.sort_order).all()
    items = Item.query.filter_by(is_available=True).all()
    return render_template('staff/menu.html', categories=categories, items=items)