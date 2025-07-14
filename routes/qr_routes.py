from flask import Blueprint, request, jsonify
from utils.helpers import check_qr_code_exists, record_visitor_visit

qr_bp = Blueprint('qr', __name__, url_prefix='/api')


@qr_bp.route('/check-qr', methods=['POST'])
def check_qr():
    data = request.get_json()
    qr_code = data.get('qr_code', '').strip()
    team_id = data.get('team_id', '').strip()

    if not qr_code:
        return jsonify({"error": "No QR code provided"}), 400

    exists = check_qr_code_exists(qr_code)

    if exists and team_id:
        result = record_visitor_visit(qr_code, team_id)
        return jsonify({
            "exists": True,
            "qr_code": qr_code,
            **result
        })

    return jsonify({"exists": exists})
