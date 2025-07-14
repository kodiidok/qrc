from flask import Blueprint, request, jsonify, render_template
import sqlite3
from datetime import datetime

team_bp = Blueprint('team', __name__)

# Define the 13 teams for the exhibition
ALLOWED_TEAMS = [
    'team1', 'team2', 'team3', 'team4', 'team5', 'team6', 'team7',
    'team8', 'team9', 'team10', 'team11', 'team12', 'team13'
]

# Minimum visits required for sticker eligibility
MIN_VISITS_FOR_STICKER = 11

DB_NAME = 'exhibition-database.db'


@team_bp.route('/team/<team_name>/scan', methods=['GET', 'POST'])
def team_scan(team_name):
    """
    Endpoint for teams to scan visitor QR codes
    """
    # Validate team name
    if team_name not in ALLOWED_TEAMS:
        return jsonify({
            'error': f'Invalid team name. Allowed teams: {", ".join(ALLOWED_TEAMS)}'
        }), 400

    if request.method == 'GET':
        return render_template('team_scan.html', team_name=team_name)

    # Handle POST request
    data = request.get_json()
    visitor_qr = data.get('visitorQR')

    if not visitor_qr:
        return jsonify({'error': 'visitorQR is required'}), 400

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()

            # Check if visitor already visited this team
            cur.execute(
                "SELECT id FROM visitor_visits WHERE visitor_qr = ? AND team_name = ?",
                (visitor_qr, team_name)
            )
            existing_visit = cur.fetchone()

            if existing_visit:
                return jsonify({
                    'message': f'Visitor has already visited {team_name}',
                    'duplicate': True,
                    'visit_id': existing_visit[0]
                }), 200

            # Insert new visit record
            cur.execute(
                "INSERT INTO visitor_visits (visitor_qr, team_name) VALUES (?, ?)",
                (visitor_qr, team_name)
            )

            # Update or insert visitor summary
            cur.execute(
                "SELECT total_visits FROM visitors WHERE visitor_qr = ?",
                (visitor_qr,)
            )
            visitor_record = cur.fetchone()

            if visitor_record:
                # Update existing visitor
                new_total = visitor_record[0] + 1
                cur.execute(
                    """UPDATE visitors 
                       SET total_visits = ?, 
                           last_visit = CURRENT_TIMESTAMP,
                           first_visit = COALESCE(first_visit, CURRENT_TIMESTAMP)
                       WHERE visitor_qr = ?""",
                    (new_total, visitor_qr)
                )
            else:
                # Insert new visitor (shouldn't happen with pre-generated QR codes)
                cur.execute(
                    """INSERT INTO visitors (visitor_qr, total_visits, first_visit, last_visit) 
                       VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                    (visitor_qr,)
                )
                new_total = 1

            conn.commit()

            return jsonify({
                'message': f'Visit to {team_name} recorded successfully',
                'visit_id': cur.lastrowid,
                'total_visits': new_total,
                'visits_remaining': max(0, MIN_VISITS_FOR_STICKER - new_total),
                'eligible_for_sticker': new_total >= MIN_VISITS_FOR_STICKER
            })

    except sqlite3.IntegrityError:
        return jsonify({
            'message': f'Visitor has already visited {team_name}',
            'duplicate': True
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
