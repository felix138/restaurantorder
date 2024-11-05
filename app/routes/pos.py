from flask import Blueprint, request, jsonify, current_app
from app.models.order import Order
from app import db
from app.config import Config

bp = Blueprint('pos', __name__, url_prefix='/pos')

def init_pos(app):
    """初始化收银机接口"""
    if not Config.POS_ENABLED:
        return
        
    # 注册蓝图
    app.register_blueprint(bp)
    
    # 可以添加其他初始化代码
    if Config.POS_TYPE == 'standard':
        # 标准收银机接口初始化
        pass
    elif Config.POS_TYPE == 'custom':
        # 自定义收银机接口初始化
        pass

@bp.before_request
def check_pos_enabled():
    """检查收银机接口是否启用"""
    if not Config.POS_ENABLED:
        return jsonify({'success': False, 'message': '收银机接口未启用'}), 403

@bp.route('/order/<order_number>', methods=['GET'])
def get_order(order_number):
    """获取订单信息，供收银机查询"""
    order = Order.query.filter_by(order_number=order_number).first()
    if not order:
        return jsonify({'success': False, 'message': '订单不存在'}), 404
    
    return jsonify({
        'success': True,
        'data': order.to_pos_format()
    })

@bp.route('/payment/callback', methods=['POST'])
def payment_callback():
    """收银机支付回调接口"""
    try:
        data = request.json
        order_number = data.get('orderNo')
        order = Order.query.filter_by(order_number=order_number).first()
        
        if not order:
            return jsonify({'success': False, 'message': '订单不存在'}), 404
        
        if order.update_from_pos(data):
            db.session.commit()
            return jsonify({
                'success': True,
                'message': '支付状态更新成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '收银机接口未启用'
            }), 403
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'支付状态更新失败: {str(e)}'
        }), 500 