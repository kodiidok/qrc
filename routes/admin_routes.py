from flask import Blueprint, request, jsonify, abort, send_file
from database import init_db, reset_db, get_db_stats
from utils.qr_generator import QRGenerator
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN')


def is_authorized():
    token = request.headers.get('Authorization')
    return token == f"Bearer {ADMIN_TOKEN}"


#
#   DB
#

@admin_bp.route('/stats')
def admin_stats():
    if not is_authorized():
        abort(403)
    return jsonify(get_db_stats())


@admin_bp.route('/init-db', methods=['POST'])
def admin_init_db():
    if not is_authorized():
        abort(403)
    init_db()
    return jsonify({"message": "Database initialized."})


@admin_bp.route('/reset-db', methods=['POST'])
def admin_reset_db():
    if not is_authorized():
        abort(403)
    reset_db()
    return jsonify({"message": "Database reset and reinitialized."})


#
#   QR
#

@admin_bp.route('/init-qr-codes', methods=['POST'])
def admin_init_qr_codes():
    if not is_authorized():
        abort(403)
    QRGenerator.init_qr_codes()
    return jsonify({"message": "QR codes initialized."})


@admin_bp.route('/reset-qr-codes', methods=['POST'])
def admin_reset_qr_codes():
    if not is_authorized():
        abort(403)
    QRGenerator.reset_qr_codes()
    return jsonify({"message": "QR codes reset."})


@admin_bp.route('/download-active-qr-codes', methods=['GET'])
def download_active_qr_codes():
    if not is_authorized():
        abort(403)
    file_path = QRGenerator.export_active_qr_codes_to_csv()
    return send_file(file_path, mimetype='text/csv', as_attachment=True, download_name='active_qr_codes.csv')
