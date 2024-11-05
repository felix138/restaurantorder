from flask import Blueprint, render_template, jsonify
from app.models.category import Category
from app.models.item import Item
from app.models.set_meal import SetMeal, SetMealItem
from sqlalchemy.orm import joinedload
import logging

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

bp = Blueprint('order', __name__)

@bp.route('/menu')
def menu():
    logger.debug("开始加载菜单页面")
    
    try:
        # 获取分类和菜品
        logger.debug("开始查询分类和菜品数据")
        categories = Category.query.order_by(Category.sort_order).all()
        logger.debug(f"找到 {len(categories)} 个分类")
        
        items = Item.query.filter_by(is_available=True).all()
        logger.debug(f"找到 {len(items)} 个可用菜品")
        
        # 查询套餐数据
        logger.debug("开始查询套餐数据")
        set_meals = SetMeal.query.filter_by(is_available=True).all()
        logger.debug(f"找到 {len(set_meals)} 个可用套餐")
        
        # 检查套餐对象
        for set_meal in set_meals:
            logger.debug(f"套餐ID: {set_meal.id}, 名称: {set_meal.name}, 价格: {set_meal.price}")
        
        set_meal_details = {}
        
        # 修改套餐菜品查询方式
        for set_meal in set_meals:
            logger.debug(f"处理套餐: {set_meal.id} - {set_meal.name}")
            
            # 直接使用 join 查询套餐菜品
            meal_items = db.session.query(SetMealItem, Item)\
                .join(Item)\
                .filter(SetMealItem.set_meal_id == set_meal.id)\
                .filter(Item.is_available == True)\
                .all()
            
            logger.debug(f"套餐 {set_meal.id} 包含 {len(meal_items)} 个菜品")
            
            items_list = []
            for smi, item in meal_items:
                logger.debug(f"添加菜品到套餐: {item.name} x {smi.quantity}")
                items_list.append({
                    'id': item.id,
                    'name': item.name,
                    'quantity': smi.quantity,
                    'price': float(item.price)
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
        
        logger.debug("菜单数据准备完成")
        logger.debug(f"分类数量: {len(categories)}")
        logger.debug(f"菜品数量: {len(items)}")
        logger.debug(f"套餐数量: {len(set_meals)}")
        logger.debug(f"套餐详情: {set_meal_details}")
        
        # 检查模板变量
        template_vars = {
            'categories': categories,
            'items': items,
            'set_meals': set_meals,
            'set_meal_details': set_meal_details
        }
        logger.debug(f"传递给模板的变量: {template_vars}")
        
        return render_template('order/menu.html', **template_vars)
        
    except Exception as e:
        logger.error(f"加载菜单页面时发生错误: {str(e)}", exc_info=True)
        return render_template('error.html', error=str(e))