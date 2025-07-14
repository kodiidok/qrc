from flask import Blueprint, request, jsonify
import sqlite3

visitor_bp = Blueprint('visitor', __name__)

# Define the 13 teams for the exhibition
ALLOWED_TEAMS = [
    'team1', 'team2', 'team3', 'team4', 'team5', 'team6', 'team7',
    'team8', 'team9', 'team10', 'team11', 'team12', 'team13'
]

# Minimum visits required for sticker eligibility
MIN_VISITS_FOR_STICKER = 11

DB_NAME = 'exhibition-database.db'


@visitor_bp.route('/visitor/status/<visitor_qr>', methods=['GET'])
def visitor_status(visitor_qr):
    """
    Check visitor's current status and progress
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Get visitor info
            cur.execute(
                "SELECT * FROM visitors WHERE visitor_qr = ?", (visitor_qr,))
            visitor = cur.fetchone()

            if not visitor:
                return jsonify({
                    'visitor_qr': visitor_qr,
                    'found': False,
                    'message': 'Visitor not found'
                }), 404

            # Get visited teams
            cur.execute("""
                SELECT team_name, visit_time 
                FROM visitor_visits 
                WHERE visitor_qr = ? 
                ORDER BY visit_time
            """, (visitor_qr,))
            visits = cur.fetchall()

            visited_teams = [visit['team_name'] for visit in visits]
            not_visited_teams = [
                team for team in ALLOWED_TEAMS if team not in visited_teams]

            return jsonify({
                'visitor_qr': visitor_qr,
                'found': True,
                'total_visits': visitor['total_visits'],
                'required_visits': MIN_VISITS_FOR_STICKER,
                'visits_remaining': max(0, MIN_VISITS_FOR_STICKER - visitor['total_visits']),
                'eligible_for_sticker': visitor['total_visits'] >= MIN_VISITS_FOR_STICKER,
                'sticker_dispensed': visitor['sticker_dispensed'],
                'visited_teams': visited_teams,
                'not_visited_teams': not_visited_teams,
                'progress_percentage': (visitor['total_visits'] / MIN_VISITS_FOR_STICKER) * 100,
                'visits': [{'team': visit['team_name'], 'time': visit['visit_time']} for visit in visits]
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Legacy endpoints for backward compatibility


@visitor_bp.route('/data', methods=['GET'])
def get_data():
    """Legacy endpoint - now shows visitor visits"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT vv.*, v.total_visits, v.sticker_dispensed 
                FROM visitor_visits vv 
                JOIN visitors v ON vv.visitor_qr = v.visitor_qr 
                ORDER BY vv.visit_time DESC
            """).fetchall()

            html = "<h1>Exhibition Visitor Visits</h1><ul>"
            for row in rows:
                html += f"<li>ID: {row['id']} | Visitor: {row['visitor_qr']} | Team: {row['team_name']} | Time: {row['visit_time']} | Total Visits: {row['total_visits']} | Sticker: {'Yes' if row['sticker_dispensed'] else 'No'}</li>"
            html += "</ul>"
            return html
    except Exception as e:
        return str(e), 500
