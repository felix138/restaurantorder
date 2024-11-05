from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('customer', __name__, url_prefix='/customer')

@bp.route('/')
@login_required
def index():
    return render_template('customer/index.html') 