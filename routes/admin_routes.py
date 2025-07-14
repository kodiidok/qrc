from database import get_db_cursor
import uuid
import csv
from flask import Blueprint, request, jsonify, abort, send_file, url_for, render_template
from database import init_db, reset_db, get_db_stats
from utils.helpers import init_teams_from_csv
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


#
#   TEAMS
#


@admin_bp.route('/init-teams', methods=['POST'])
def admin_init_teams():
    if not is_authorized():
        abort(403)

    csv_path = os.path.join('static', 'data', 'teams.csv')

    try:
        result = init_teams_from_csv(csv_path)
        return jsonify({
            "message": "Team initialization completed.",
            **result
        })
    except FileNotFoundError:
        return jsonify({"error": "CSV file not found"}), 404


@admin_bp.route('/team-scanner-urls', methods=['GET'])
def get_team_scanner_urls():
    if not is_authorized():
        abort(403)

    with get_db_cursor() as cursor:
        cursor.execute("SELECT id, team_name FROM teams")
        teams = cursor.fetchall()

    # Construct URLs
    scanner_urls = [
        {
            "team_name": team["team_name"],
            "scanner_url": url_for("team.team_scan_qr", team_id=team["id"], _external=True)
        }
        for team in teams
    ]

    return jsonify(scanner_urls)
