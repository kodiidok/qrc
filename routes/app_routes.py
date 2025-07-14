from flask import Blueprint, render_template, current_app

app_bp = Blueprint('app_routes', __name__)


@app_bp.route('/')
def home():
    return f"App is running with config: {current_app.config['DB_NAME']}"


@app_bp.route('/scan-qr')
def scan_qr():
    return render_template('scan_qr.html')


@app_bp.route('/check-visitor')
def admin_visitor_scanner():
    return render_template('check-visitor.html')
