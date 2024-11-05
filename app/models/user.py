from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.models.role import Role

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    real_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    status = db.Column(db.Boolean, default=True)
    
    role = db.relationship('Role', backref='users', lazy=True)
    
    def set_password(self, password):
        """设置密码，使用默认的pbkdf2:sha256方法"""
        self.password = generate_password_hash(password)
        
    def check_password(self, password):
        """验证密码"""
        try:
            # 如果密码是明文存储的（旧密码），直接比较
            if len(self.password) < 60:  # 哈希密码通常长度大于60
                if self.password == password:
                    # 自动升级到哈希密码
                    self.set_password(password)
                    db.session.commit()
                    return True
                return False
            # 否则使用哈希验证
            return check_password_hash(self.password, password)
        except Exception as e:
            # 记录错误但不暴露详细信息
            print(f"Password check error: {str(e)}")
            return False

    def get_id(self):
        """返回用户ID的字符串表示"""
        return str(self.id)

    def is_active(self):
        """检查用户是否激活"""
        return self.status

    def is_authenticated(self):
        """检查用户是否已认证"""
        return True

    def is_anonymous(self):
        """检查是否是匿名用户"""
        return False

@login_manager.user_loader
def load_user(id):
    try:
        return User.query.get(int(id))
    except Exception as e:
        print(f"User load error: {str(e)}")
        return None 