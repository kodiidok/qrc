from flask import Blueprint, request, jsonify
from utils.helpers import check_qr_code_exists

qr_bp = Blueprint('qr', __name__, url_prefix='/api')


@qr_bp.route('/check-qr', methods=['POST'])
def check_qr():
    data = request.get_json()
    qr_code = data.get('qr_code', '').strip()

    print(f"[QR CHECK] Received QR code: '{qr_code}'")  # Debug print

    if not qr_code:
        return jsonify({"error": "No QR code provided"}), 400

    exists = check_qr_code_exists(qr_code)

    return jsonify({"exists": exists, "qr_code": qr_code} if exists else {"exists": False})
