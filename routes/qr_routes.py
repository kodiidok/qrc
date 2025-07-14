from flask import Blueprint, request, jsonify
from database.database import get_db_cursor, get_visitor_by_qr, get_visitor_visit_log
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


@qr_bp.route('/check-visitor', methods=['POST'])
def check_visitor():
    data = request.get_json()
    qr_code = data.get('qr_code', '').strip()

    if not qr_code:
        return jsonify({"error": "No QR code provided"}), 400

    with get_db_cursor() as cursor:
        # Get total visits
        visitor = get_visitor_by_qr(qr_code)

        if not visitor:
            return jsonify({"exists": False, "message": "Visitor not found"}), 404

        total_visits = visitor["total_visits"]

        if total_visits < 10:
            return jsonify({
                "exists": True,
                "enough_visits": False,
                "total_visits": total_visits,
                "message": "Visitor has not completed 10 visits yet."
            })

        # Get visit log
        visits = get_visitor_visit_log(qr_code)

        visits_log = [
            {"team_name": v["team_name"], "visit_time": v["visit_time"]}
            for v in visits
        ]

    return jsonify({
        "exists": True,
        "enough_visits": True,
        "total_visits": total_visits,
        "visits": visits_log
    })
