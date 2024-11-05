from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models.user import User
from app.models.role import Role
from app.models.setting import Setting
from app import db
import os

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@login_required
def index():
    if current_user.role_id != 1:  # 确保只有管理员可以访问
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    return render_template('admin/index.html')

@bp.route('/users')
@login_required
def users():
    if current_user.role_id != 1:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@bp.route('/users/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_user(id):
    if current_user.role_id != 1:
        return {'success': False, 'message': '没有权限执行此操作'}, 403
    
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        return {'success': False, 'message': '不能禁用自己的账号'}, 400
    
    user.status = not user.status
    db.session.commit()
    return {'success': True}

@bp.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role_id != 1:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role_id = request.form['role_id']
        real_name = request.form['real_name']
        phone = request.form['phone']
        email = request.form['email']
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
            return redirect(url_for('admin.add_user'))
        
        user = User(
            username=username,
            password=password,  # 这里暂时使用明文密码
            role_id=role_id,
            real_name=real_name,
            phone=phone,
            email=email,
            status=True
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('用户添加成功')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash('用户添加失败')
            return redirect(url_for('admin.add_user'))
    
    roles = Role.query.all()
    return render_template('admin/add_user.html', roles=roles)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role_id != 1:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # 处理设置更新
        settings_data = {
            'restaurant_name': request.form.get('restaurant_name'),
            'contact_phone': request.form.get('contact_phone'),
            'business_hours': request.form.get('business_hours'),
            'member_discount': request.form.get('member_discount'),
            'points_rate': request.form.get('points_rate'),
            'enable_member': request.form.get('enable_member') == 'on',
            'enable_points': request.form.get('enable_points') == 'on'
        }
        
        for key, value in settings_data.items():
            setting = Setting.query.filter_by(key=key).first()
            if setting:
                setting.value = str(value)
                setting.updated_by = current_user.id
            else:
                setting = Setting(
                    key=key,
                    value=str(value),
                    updated_by=current_user.id
                )
                db.session.add(setting)
        
        try:
            db.session.commit()
            flash('设置已更新')
        except Exception as e:
            db.session.rollback()
            flash('设置更新失败')
        
        return redirect(url_for('admin.settings'))
    
    # 获取当前设置
    settings = {}
    for setting in Setting.query.all():
        settings[setting.key] = setting.value
    
    return render_template('admin/settings.html', settings=settings)

@bp.route('/logs')
@login_required
def get_logs():
    if current_user.role_id != 1:
        return jsonify({'error': '没有权限访问'}), 403
    
    try:
        # 读取日志文件
        log_file = 'app.log'  # 根据实际的日志文件路径修改
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.read()
        else:
            logs = "暂无日志记录"
        
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': f'读取日志失败: {str(e)}'}), 500

@bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if current_user.role_id != 1:
        flash('没有权限访问该页面')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(id)
    roles = Role.query.all()
    
    if request.method == 'POST':
        try:
            user.username = request.form['username']
            if request.form.get('password'):  # 只有当提供了新密码时才更新密码
                user.set_password(request.form['password'])
            user.role_id = request.form['role_id']
            user.real_name = request.form['real_name']
            user.phone = request.form['phone']
            user.email = request.form['email']
            user.status = 'status' in request.form
            
            db.session.commit()
            flash('用户信息更新成功')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash('用户信息更新失败：' + str(e))
            return redirect(url_for('admin.edit_user', id=id))
    
    return render_template('admin/edit_user.html', user=user, roles=roles)