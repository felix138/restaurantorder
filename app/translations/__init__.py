from flask_babel import Babel

babel = Babel()

def init_babel(app):
    babel.init_app(app)
    
    @babel.localeselector
    def get_locale():
        from flask import session
        return session.get('lang', 'zh') 