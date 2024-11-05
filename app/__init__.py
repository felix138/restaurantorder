from flask import Flask, redirect, url_for, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_babel import Babel
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
babel = Babel()

def get_locale():
    # 从 session 中获取语言设置，如果没有则返回默认值
    return session.get('lang', 'zh')

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    
    # 初始化 Babel
    babel.init_app(app)
    babel.localeselector(get_locale)  # 使用装饰器方式设置语言选择器
    
    # 语言切换路由
    @app.route('/set_language/<lang>')
    def set_language(lang):
        if lang in ['zh', 'en', 'no']:
            session['lang'] = lang
        return redirect(request.referrer or url_for('index'))

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role_id == 1:  # admin
                return redirect(url_for('admin.index'))
            elif current_user.role_id == 2:  # manager
                return redirect(url_for('manager.index'))
            elif current_user.role_id == 3:  # staff
                return redirect(url_for('staff.index'))
            else:  # customer
                return redirect(url_for('customer.index'))
        return redirect(url_for('auth.login'))

    # 注册蓝图
    from app.routes.auth import bp as auth_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.manager import bp as manager_bp
    from app.routes.staff import bp as staff_bp
    from app.routes.customer import bp as customer_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(customer_bp)

    return app