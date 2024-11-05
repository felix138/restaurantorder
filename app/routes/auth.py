from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db
import logging

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('请输入用户名和密码')
                return render_template('auth/login.html')
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                if not user.is_active():
                    flash('账号已被禁用')
                    return render_template('auth/login.html')
                
                login_user(user)
                return redirect(url_for('index'))
            
            flash('用户名或密码错误')
        except Exception as e:
            logging.error(f"Login error: {str(e)}")
            flash('登录时发生错误，请稍后重试')
            
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    try:
        logout_user()
    except Exception as e:
        logging.error(f"Logout error: {str(e)}")
    return redirect(url_for('auth.login'))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            current_user.real_name = request.form.get('real_name')
            current_user.phone = request.form.get('phone')
            current_user.email = request.form.get('email')
            
            db.session.commit()
            flash('个人信息更新成功')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Profile update error: {str(e)}")
            flash('个人信息更新失败')
        
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html')

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not all([current_password, new_password, confirm_password]):
                flash('请填写所有密码字段')
                return redirect(url_for('auth.change_password'))
            
            if not current_user.check_password(current_password):
                flash('当前密码错误')
                return redirect(url_for('auth.change_password'))
            
            if new_password != confirm_password:
                flash('两次输入的新密码不一致')
                return redirect(url_for('auth.change_password'))
            
            if len(new_password) < 6:
                flash('新密码长度不能小于6位')
                return redirect(url_for('auth.change_password'))
            
            current_user.set_password(new_password)
            db.session.commit()
            flash('密码修改成功')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Password change error: {str(e)}")
            flash('密码修改失败')
            return redirect(url_for('auth.change_password'))
    
    return render_template('auth/change_password.html')