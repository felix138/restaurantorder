from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
from app.models.item import Item
from app.models.category import Category
from app.models.order import Order, OrderItem
from app.models.set_meal import SetMeal, SetMealItem
from app.models.staff import Staff
from app.models.user import User
from app import db
from datetime import datetime, timedelta
import logging
import sys
import os
from werkzeug.utils import secure_filename
import codecs
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd
from io import BytesIO
import base64
import matplotlib
matplotlib.use('Agg')  # 设置后端为 Agg
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 设置中文字体，这里使用微软雅黑，它支持¥符号
font = FontProperties(fname=r'C:\Windows\Fonts\msyh.ttc', size=12)
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 设置默认字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 配置日志处理器使用 UTF-8 编码
handler = logging.StreamHandler(codecs.getwriter('utf-8')(sys.stdout.buffer))
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# 移除任何现有的处理器
for h in logger.handlers[:]:
    logger.removeHandler(h)
logger.addHandler(handler)

bp = Blueprint('manager', __name__, url_prefix='/manager')

# 添加文件上传配置
UPLOAD_FOLDER = 'app/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
@login_required
def index():
    if current_user.role_id != 2:  # 确保是经理角色
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    return render_template('manager/index.html')

@bp.route('/items')
@login_required
def items():
    if current_user.role_id != 2:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    items = Item.query.all()
    categories = Category.query.order_by(Category.sort_order).all()
    return render_template('manager/items.html', items=items, categories=categories)

@bp.route('/set_meals')
@login_required
def set_meals():
    if current_user.role_id != 2:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    set_meals = SetMeal.query.all()
    categories = Category.query.order_by(Category.sort_order).all()
    items = Item.query.filter_by(is_available=True).all()
    return render_template('manager/set_meals.html', 
                         set_meals=set_meals, 
                         categories=categories,
                         items=items)

@bp.route('/categories')
@login_required
def categories():
    if current_user.role_id != 2:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    try:
        # 按照排序号升序获取分类列表
        categories = Category.query.order_by(Category.sort_order).all()
        return render_template('manager/categories.html', categories=categories)
    except Exception as e:
        logger.error(f"获取分类列表失败: {str(e)}", exc_info=True)
        flash('获取分类列表失败')
        return redirect(url_for('index'))

@bp.route('/staff')
@login_required
def staff():
    if current_user.role_id != 2:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    staff_list = Staff.query.all()
    return render_template('manager/staff.html', staff_list=staff_list)

@bp.route('/reports')
@login_required
def reports():
    if current_user.role_id != 2:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    try:
        # 获取查询日期范围
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # 包含结束日期
        else:
            # 默认最近30天
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
        
        # 获取已完成的订单数据
        orders = Order.query.filter(
            Order.created_at.between(start_date, end_date),
            Order.status == 'completed'
        ).all()
        
        # 计算基础统计数据
        total_revenue = sum(float(order.actual_amount) for order in orders)
        total_orders = len(orders)
        average_order = total_revenue / total_orders if total_orders > 0 else 0
        
        # 获取热销商品数据
        hot_items_query = db.session.query(
            Item.name,
            db.func.sum(OrderItem.quantity).label('total_quantity')
        ).join(OrderItem).join(Order).filter(
            Order.created_at.between(start_date, end_date),
            Order.status == 'completed'
        ).group_by(Item.id).order_by(
            db.desc('total_quantity')
        ).limit(5).all()
        
        hot_items_data = [
            {
                'name': item.name,
                'count': int(item.total_quantity)
            } for item in hot_items_query
        ]
        
        # 创建趋势图
        plt.figure(figsize=(10, 6))
        plt.clf()
        
        # 获取每日营业额数据
        daily_revenues = {}
        dates = []
        revenues = []
        details = []
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            dates.append(date_str)
            
            # 计算当日营业额
            daily_orders = [order for order in orders if order.created_at.date() == current_date.date()]
            daily_revenue = sum(float(order.actual_amount) for order in daily_orders)
            revenues.append(daily_revenue)
            
            if daily_orders:
                daily_count = len(daily_orders)
                top_item = db.session.query(
                    Item.name,
                    db.func.sum(OrderItem.quantity).label('total_quantity')
                ).join(OrderItem).join(Order).filter(
                    Order.created_at >= datetime.combine(current_date.date(), datetime.min.time()),
                    Order.created_at < datetime.combine(current_date.date() + timedelta(days=1), datetime.min.time()),
                    Order.status == 'completed'
                ).group_by(Item.id).order_by(
                    db.desc('total_quantity')
                ).first()
                
                details.append({
                    'date': date_str,
                    'orderCount': daily_count,
                    'revenue': daily_revenue,
                    'averageOrder': daily_revenue / daily_count if daily_count > 0 else 0,
                    'topItem': top_item.name if top_item else '-'
                })
            
            current_date += timedelta(days=1)
        
        # 绘制趋势图
        plt.plot(range(len(dates)), revenues, marker='o', linestyle='-', color='#4e73df')
        plt.title('每日营业额趋势', fontsize=14)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('营业额', fontsize=12)
        plt.xticks(range(len(dates)), dates, rotation=45)
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()

        # 删除第一个图表创建，只保留组合图表
        # 创建图表
        plt.figure(figsize=(20, 6))
        
        # 1. 营业额趋势图 (左边)
        plt.subplot(1, 2, 1)
        plt.plot(range(len(dates)), revenues, marker='o', linestyle='-', color='#4e73df')
        plt.title('每日营业额趋势', fontsize=14)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('营业额', fontsize=12)
        plt.xticks(range(len(dates)), dates, rotation=45)
        plt.grid(True, linestyle='--', alpha=0.5)
        
        # 2. 热销商品饼图 (右边)
        plt.subplot(1, 2, 2)
        if hot_items_data:  # 确保有数据
            labels = [f"{item['name']}\n({item['count']}份)" for item in hot_items_data]  # 添加销量到标签
            sizes = [item['count'] for item in hot_items_data]
            colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b']
            
            plt.pie(sizes, 
                   labels=labels,
                   colors=colors,
                   autopct='%1.1f%%',
                   startangle=90)
            plt.title('热销商品TOP5', fontsize=14)
            plt.axis('equal')  # 使饼图为正圆形
        else:
            plt.text(0.5, 0.5, '暂无数据', 
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=plt.gca().transAxes)
        
        plt.tight_layout(pad=3.0)  # 增加子图之间的间距

        # 将图表转换为 base64 字符串
        img = BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight', dpi=100)
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close()  # 确保关闭图表
        
        # 打印调试信息
        logger.debug(f"Total Revenue: {total_revenue}")
        logger.debug(f"Total Orders: {total_orders}")
        logger.debug(f"Average Order: {average_order}")
        logger.debug(f"Hot Items Count: {len(hot_items_data)}")
        logger.debug(f"Dates Count: {len(dates)}")
        logger.debug(f"Revenues Count: {len(revenues)}")
        
        # 确保所有数据都被正确传递到模板
        return render_template('manager/reports.html',
                             total_revenue=round(total_revenue, 2),  # 四舍五入到2位小数
                             total_orders=total_orders,
                             average_order=round(average_order, 2),  # 四舍五入到2位小数
                             dates=dates,
                             revenues=revenues,
                             hot_items=hot_items_data,
                             details=details,
                             plot_url=plot_url,
                             start_date=start_date.strftime('%Y-%m-%d'),  # 添加日期范围
                             end_date=(end_date - timedelta(days=1)).strftime('%Y-%m-%d'))
                             
    except Exception as e:
        logger.error(f"Error getting report data: {str(e)}", exc_info=True)
        flash('获取报表数据失败：' + str(e))
        return render_template('manager/reports.html',
                             total_revenue=0,
                             total_orders=0,
                             average_order=0,
                             dates=[],
                             revenues=[],
                             hot_items=[],
                             details=[],
                             plot_url='',
                             start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                             end_date=datetime.now().strftime('%Y-%m-%d'))

@bp.route('/orders')
@login_required
def orders():
    # 允许经理和员工访问
    if current_user.role_id not in [2, 3]:  # 2是经理，3是员工
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    try:
        # 获取所有订单，并确保的staff和user数据也被加载
        orders = Order.query.join(Staff).join(User).order_by(Order.created_at.desc()).all()
        
        # 获取每个订单的菜品详情
        order_details = {}
        for order in orders:
            items = []
            for order_item in order.items:
                if order_item.item:  # 确保菜品存在
                    items.append({
                        'name': order_item.item.name,
                        'quantity': order_item.quantity,
                        'price': float(order_item.original_price),
                        'actual_price': float(order_item.actual_price)
                    })
            order_details[order.id] = items
        
        return render_template('manager/orders.html', 
                             orders=orders,
                             order_details=order_details)
    
    except Exception as e:
        db.session.rollback()  # 回滚任何未完成的事务
        flash('获取订单列表失败：' + str(e))
        return redirect(url_for('index'))

@bp.route('/items/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    if current_user.role_id != 2:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    item = Item.query.get_or_404(id)
    categories = Category.query.all()
    
    if request.method == 'POST':
        try:
            item.name = request.form['name']
            item.category_id = int(request.form['category_id'])
            item.price = float(request.form['price'])
            item.member_price = float(request.form['member_price']) if request.form['member_price'] else None
            item.description = request.form['description']
            item.stock_quantity = int(request.form['stock_quantity'])
            item.is_available = 'is_available' in request.form
            item.updated_by = current_user.id
            item.updated_at = datetime.utcnow()
            
            # 处理图片
            if 'remove_image' in request.form and item.image_url:
                # 除物理文件
                file_path = os.path.join('app', item.image_url.lstrip('/'))
                if os.path.exists(file_path):
                    os.remove(file_path)
                item.image_url = None
            
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    # 删除旧图片
                    if item.image_url:
                        old_file_path = os.path.join('app', item.image_url.lstrip('/'))
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    # 保存新图片
                    filename = secure_filename(file.filename)
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                    file.save(file_path)
                    item.image_url = f'/static/uploads/{unique_filename}'
            
            db.session.commit()
            flash('菜品更新成功')
            return redirect(url_for('manager.items'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'菜品更新失败: {str(e)}')
            return redirect(url_for('manager.edit_item', id=id))
    
    return render_template('manager/edit_item.html', item=item, categories=categories)

@bp.route('/items/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if current_user.role_id != 2:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    categories = Category.query.all()
    
    if request.method == 'POST':
        # 图传
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # 确保上传目存在
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                # 生成唯一文件名
                unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                # 生成相对URL
                image_url = f'/static/uploads/{unique_filename}'
        
        item = Item(
            name=request.form['name'],
            category_id=int(request.form['category_id']),
            price=float(request.form['price']),
            member_price=float(request.form['member_price']) if request.form['member_price'] else None,
            description=request.form['description'],
            image_url=image_url,  # 添加图片URL
            stock_quantity=int(request.form['stock_quantity']),
            is_available='is_available' in request.form,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        
        try:
            db.session.add(item)
            db.session.commit()
            flash('菜品添加成功')
            return redirect(url_for('manager.items'))
        except Exception as e:
            db.session.rollback()
            flash('菜品添加失败')
            return redirect(url_for('manager.add_item'))
    
    return render_template('manager/add_item.html', categories=categories)

@bp.route('/items/<int:id>/delete', methods=['POST'])
@login_required
def delete_item(id):
    if current_user.role_id != 2:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    item = Item.query.get_or_404(id)
    try:
        db.session.delete(item)
        db.session.commit()
        return {'success': True}
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': str(e)}

from sqlalchemy import text
from contextlib import contextmanager

# 添加一个分布式锁的上下文管理器
@contextmanager
def distributed_lock(session, lock_name, timeout=10):
    try:
        # 尝试获取锁
        result = session.execute(
            text("SELECT GET_LOCK(:lock_name, :timeout)"),
            {'lock_name': lock_name, 'timeout': timeout}
        )
        if result.scalar() == 1:
            yield True
        else:
            yield False
    finally:
        # 释放锁
        session.execute(
            text("SELECT RELEASE_LOCK(:lock_name)"),
            {'lock_name': lock_name}
        )

# 创建一个内存锁字典，用于存储每个分类名称的锁定状态
category_locks = {}
lock_timeout = 5  # 锁定超时时间（秒）

@bp.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    if current_user.role_id != 2:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        logger.debug(f"开始添加分类，接收到的数据：{data}")
        
        if not name:
            logger.debug("分类名称为空")
            return {'success': False, 'message': '分类名称不能为空'}, 400

        # 检查是否已存在相同名称的分类（忽略大小写）
        logger.debug(f"检查是否存在相同名称的分类：{name}")
        existing_category = db.session.query(Category).filter(
            db.func.lower(Category.name) == db.func.lower(name)
        ).first()
        
        if existing_category:
            logger.debug(f"发现重复分类：ID={existing_category.id}, 名称={existing_category.name}")
            return {'success': False, 'message': '已存在相同名称的分类'}, 400
            
        # 获取当前最大排序号
        max_sort = db.session.query(db.func.max(Category.sort_order)).scalar()
        new_sort_order = (max_sort or 0) + 1
        logger.debug(f"生成新的排序号：{new_sort_order}（当前最大排序号：{max_sort}）")
        
        # 创建新分类
        category = Category(
            name=name,
            description=description,  # 添加描述字段
            sort_order=new_sort_order,
            created_by=current_user.id
        )
        
        logger.debug(f"准备添加新分类：name={name}, sort_order={new_sort_order}")
        db.session.add(category)
        db.session.commit()
        
        logger.debug(f"分类添加成功：ID={category.id}, 名称={category.name}, 排序号={category.sort_order}")
        
        # 返回新创建的分类信息
        return {
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'sort_order': category.sort_order
            }
        }
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"添加分类失败: {str(e)}", exc_info=True)
        logger.error(f"错误详情：\n请求数据：{request.get_json()}\n当前用户ID：{current_user.id}")
        return {'success': False, 'message': f'添加分类失败: {str(e)}'}, 500

@bp.route('/categories/<int:id>/edit', methods=['POST'])
@login_required
def edit_category(id):
    if current_user.role_id != 2:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    category = Category.query.get_or_404(id)
    data = request.get_json()
    
    try:
        # 检查名称是否重复（排除当前分类）
        existing = Category.query.filter(
            Category.name == data['name'],
            Category.id != id
        ).first()
        if existing:
            return {'success': False, 'message': '已存在相同名称的分类'}, 400
        
        # 如果修改了排序号
        if 'sort_order' in data and int(data['sort_order']) != category.sort_order:
            new_sort = int(data['sort_order'])
            # 获取最大和最小排序号
            min_sort = db.session.query(db.func.min(Category.sort_order)).scalar() or 1
            max_sort = db.session.query(db.func.max(Category.sort_order)).scalar() or 1
            
            # 确保排序号在有效范围内
            if new_sort < min_sort:
                new_sort = min_sort
            elif new_sort > max_sort:
                new_sort = max_sort
                
            # 更新其他分类的排序号
            if new_sort > category.sort_order:
                # 向下移动
                Category.query.filter(
                    Category.sort_order > category.sort_order,
                    Category.sort_order <= new_sort
                ).update({Category.sort_order: Category.sort_order - 1})
            else:
                # 向上移动
                Category.query.filter(
                    Category.sort_order >= new_sort,
                    Category.sort_order < category.sort_order
                ).update({Category.sort_order: Category.sort_order + 1})
            
            category.sort_order = new_sort
        
        category.name = data['name']
        category.description = data.get('description', '').strip()  # 添加描述字段的处理
        category.updated_by = current_user.id
        category.updated_at = datetime.utcnow()
        
        db.session.commit()
        return {'success': True}
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"编辑分类失败: {str(e)}", exc_info=True)
        return {'success': False, 'message': str(e)}

@bp.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
def delete_category(id):
    if current_user.role_id != 2:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    try:
        # 检查分类是否存在
        category = Category.query.get(id)  # 使用 get 而不是 get_or_404
        
        if not category:
            return {'success': False, 'message': '分类不存在或已被删除'}, 404
        
        # 检查是否有关联的菜品
        if Item.query.filter_by(category_id=id).first():
            return {'success': False, 'message': '该分类下还有菜品，无法删除'}, 400
        
        # 获取当前分类的排序号
        current_sort = category.sort_order
        
        # 删除分类
        db.session.delete(category)
        
        # 更新其他分类的排序号
        Category.query.filter(Category.sort_order > current_sort).update(
            {Category.sort_order: Category.sort_order - 1}
        )
        
        db.session.commit()
        return {'success': True}
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除分类失败: {str(e)}", exc_info=True)
        return {'success': False, 'message': f'删除分类失败: {str(e)}'}, 500

@bp.route('/set_meals/add', methods=['POST'])
@login_required
def add_set_meal():
    if current_user.role_id != 2:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    data = request.get_json()
    set_meal = SetMeal(
        name=data['name'],
        price=float(data['price']),
        member_price=float(data['member_price']) if data['member_price'] else None,
        description=data['description'],
        created_by=current_user.id
    )
    
    try:
        db.session.add(set_meal)
        db.session.flush()  # 获取set_meal.id
        
        # 添加套餐菜品关联
        for item_id in data['items']:
            set_meal_item = SetMealItem(
                set_meal_id=set_meal.id,
                item_id=int(item_id),
                quantity=1  # 默认数量为1
            )
            db.session.add(set_meal_item)
        
        db.session.commit()
        return {'success': True}
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': str(e)}

@bp.route('/set_meals/<int:id>/items')
@login_required
def get_set_meal_items(id):
    if current_user.role_id != 2:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    set_meal = SetMeal.query.get_or_404(id)
    items = []
    for smi in set_meal.items:
        items.append({
            'id': smi.item.id,
            'name': smi.item.name,
            'quantity': smi.quantity
        })
    return {'items': items}

@bp.route('/set_meals/<int:id>/delete', methods=['POST'])
@login_required
def delete_set_meal(id):
    if current_user.role_id != 2:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    set_meal = SetMeal.query.get_or_404(id)
    try:
        # 删除套餐品关联
        SetMealItem.query.filter_by(set_meal_id=id).delete()
        db.session.delete(set_meal)
        db.session.commit()
        return {'success': True}
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': str(e)}

@bp.route('/set_meals/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_set_meal(id):
    if current_user.role_id != 2:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    set_meal = SetMeal.query.get_or_404(id)
    categories = Category.query.order_by(Category.sort_order).all()
    items = Item.query.filter_by(is_available=True).all()
    
    # 获取当前套餐包含的菜品ID列表
    selected_items = [smi.item_id for smi in set_meal.items]
    
    if request.method == 'POST':
        set_meal.name = request.form['name']
        set_meal.price = float(request.form['price'])
        set_meal.member_price = float(request.form['member_price']) if request.form['member_price'] else None
        set_meal.description = request.form['description']
        set_meal.is_available = 'is_available' in request.form
        set_meal.updated_by = current_user.id
        set_meal.updated_at = datetime.utcnow()
        
        try:
            # 删除原有的套餐-菜品关联
            SetMealItem.query.filter_by(set_meal_id=id).delete()
            
            # 添加新的套餐-菜品关联
            selected_item_ids = request.form.getlist('items')
            for item_id in selected_item_ids:
                set_meal_item = SetMealItem(
                    set_meal_id=id,
                    item_id=int(item_id),
                    quantity=1
                )
                db.session.add(set_meal_item)
            
            db.session.commit()
            flash('套餐更新成功')
            return redirect(url_for('manager.set_meals'))
        except Exception as e:
            db.session.rollback()
            flash('套餐更新失败')
            return redirect(url_for('manager.edit_set_meal', id=id))
    
    return render_template('manager/edit_set_meal.html', 
                         set_meal=set_meal, 
                         categories=categories,
                         items=items,
                         selected_items=selected_items)

@bp.route('/orders/<int:id>/details')
@login_required
def get_order_details(id):
    if current_user.role_id not in [2, 3]:
        return jsonify({'success': False, 'message': 'No permission'}), 403
    
    try:
        logger.debug(f"Getting order details for order {id}")
        order = Order.query.get_or_404(id)
        logger.debug(f"Found order: {order.order_number}")
        
        # 构建响应数据
        response_data = {
            'order_number': order.order_number,
            'table_number': order.table_number,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'items': [],
            'total_amount': float(order.total_amount),
            'actual_amount': float(order.actual_amount)
        }
        
        # 添加订单项
        for order_item in order.items:
            if order_item.item:
                response_data['items'].append({
                    'name': order_item.item.name,
                    'quantity': order_item.quantity,
                    'price': float(order_item.original_price),
                    'actual_price': float(order_item.actual_price)
                })
        
        logger.debug(f"Order details prepared: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting order details: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/orders/<int:id>/status', methods=['POST'])
@login_required
def update_order_status(id):
    # 允许经理和员工更新订单状态
    if current_user.role_id not in [2, 3]:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    try:
        logger.debug(f"正在更新订单 {id} 的状态")
        order = Order.query.get_or_404(id)
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return {'success': False, 'message': '未提供新状态'}, 400
            
        logger.debug(f"订单状态从 {order.status} 更新为 {new_status}")
        order.status = new_status
        
        if new_status == 'completed':
            order.completed_at = datetime.utcnow()
            logger.debug(f"订单完成时间设置为: {order.completed_at}")
        
        db.session.commit()
        logger.debug("订单状态更新成功")
        return {'success': True}
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新订单状态失败: {str(e)}", exc_info=True)
        return {'success': False, 'message': str(e)}, 500

@bp.route('/staff/add', methods=['POST'])
@login_required
def add_staff():
    if current_user.role_id != 2:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    # 创建用户账号
    user = User(
        username=request.form['username'],
        password=request.form['password'],
        role_id=3,  # 员工角色
        real_name=request.form['real_name'],
        phone=request.form['phone'],
        status=True
    )
    
    try:
        db.session.add(user)
        db.session.flush()  # 获取user.id
        
        # 创建员工信息
        staff = Staff(
            user_id=user.id,
            employee_id=request.form['employee_id'],
            department=request.form['department'],
            position=request.form['position'],
            hire_date=datetime.strptime(request.form['hire_date'], '%Y-%m-%d').date()
        )
        
        db.session.add(staff)
        db.session.commit()
        return {'success': True}
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': str(e)}

@bp.route('/staff/<int:id>/delete', methods=['POST'])
@login_required
def delete_staff(id):
    if current_user.role_id != 2:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    staff = Staff.query.get_or_404(id)
    try:
        # 删除员信息和用户账号
        user_id = staff.user_id
        db.session.delete(staff)
        User.query.filter_by(id=user_id).delete()
        db.session.commit()
        return {'success': True}
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': str(e)}

@bp.route('/get_report_data', methods=['POST'])
@login_required
def get_report_data():
    if current_user.role_id != 2:
        return jsonify({'error': '没有权限访问'}), 403
    
    try:
        data = request.get_json()
        start_date = datetime.strptime(data['startDate'], '%Y-%m-%d')
        end_date = datetime.strptime(data['endDate'], '%Y-%m-%d')
        report_type = data['reportType']
        
        # 获取订单数据
        orders = Order.query.filter(
            Order.created_at.between(start_date, end_date),
            Order.status == 'completed'
        ).all()
        
        # 计算总营业额和订单数
        total_revenue = sum(float(order.actual_amount) for order in orders)
        total_orders = len(orders)
        average_order = total_revenue / total_orders if total_orders > 0 else 0
        
        # 获取热销商品
        hot_items = db.session.query(
            Item.name,
            db.func.sum(OrderItem.quantity).label('total_quantity')
        ).join(OrderItem).join(Order).filter(
            Order.created_at.between(start_date, end_date),
            Order.status == 'completed'
        ).group_by(Item.id).order_by(
            db.desc('total_quantity')
        ).limit(5).all()
        
        # 准备返回数据
        response_data = {
            'totalRevenue': total_revenue,
            'totalOrders': total_orders,
            'averageOrder': average_order,
            'hotItems': [{'name': item.name, 'count': int(item.total_quantity)} for item in hot_items],
            'dates': [],
            'revenues': [],
            'details': []
        }
        
        # 根据报表类型生成时间序列数据
        current_date = start_date
        while current_date <= end_date:
            daily_orders = [order for order in orders if order.created_at.date() == current_date.date()]
            daily_revenue = sum(float(order.actual_amount) for order in daily_orders)
            daily_count = len(daily_orders)
            
            response_data['dates'].append(current_date.strftime('%Y-%m-%d'))
            response_data['revenues'].append(daily_revenue)
            
            if daily_count > 0:
                top_item = db.session.query(
                    Item.name,
                    db.func.sum(OrderItem.quantity).label('total_quantity')
                ).join(OrderItem).join(Order).filter(
                    Order.created_at.between(
                        current_date,
                        current_date + timedelta(days=1)
                    ),
                    Order.status == 'completed'
                ).group_by(Item.id).order_by(
                    db.desc('total_quantity')
                ).first()
                
                response_data['details'].append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'orderCount': daily_count,
                    'revenue': daily_revenue,
                    'averageOrder': daily_revenue / daily_count,
                    'topItem': top_item.name if top_item else '-'
                })
            
            current_date += timedelta(days=1)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"获取报表数据失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.route('/categories/update-order', methods=['POST'])
@login_required
def update_category_order():
    if current_user.role_id != 2:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    try:
        data = request.get_json()
        updates = data.get('updates', [])
        
        # 获取所有需要更新的分类
        categories = Category.query.filter(
            Category.id.in_([u['id'] for u in updates])
        ).all()
        
        # 创建ID到分类的映射
        category_map = {c.id: c for c in categories}
        
        # 更新排序号
        for update in updates:
            category = category_map.get(update['id'])
            if category:
                category.sort_order = update['sort_order']
                category.updated_by = current_user.id
                category.updated_at = datetime.utcnow()
        
        db.session.commit()
        return {'success': True}
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新分类排序失败: {str(e)}", exc_info=True)
        return {'success': False, 'message': str(e)}, 500