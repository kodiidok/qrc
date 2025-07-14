from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime
import socket

app = Flask(__name__)
DB_NAME = 'exhibition-database.db'

# Define the 13 teams for the exhibition
ALLOWED_TEAMS = [
    'team1', 'team2', 'team3', 'team4', 'team5', 'team6', 'team7',
    'team8', 'team9', 'team10', 'team11', 'team12', 'team13'
]

# Minimum visits required for sticker eligibility
MIN_VISITS_FOR_STICKER = 11

# Ensure table exists


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS visitor_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_qr TEXT NOT NULL,
                team_name TEXT NOT NULL,
                visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(visitor_qr, team_name)
            )
        ''')

        # Optional: Create a visitors table to track additional visitor info
        conn.execute('''
            CREATE TABLE IF NOT EXISTS visitors (
                visitor_qr TEXT PRIMARY KEY,
                first_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_visits INTEGER DEFAULT 0,
                sticker_dispensed BOOLEAN DEFAULT FALSE,
                sticker_dispensed_time TIMESTAMP
            )
        ''')


init_db()


@app.route('/team/<team_name>/scan', methods=['GET', 'POST'])
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
                    "UPDATE visitors SET total_visits = ?, last_visit = CURRENT_TIMESTAMP WHERE visitor_qr = ?",
                    (new_total, visitor_qr)
                )
            else:
                # Insert new visitor
                cur.execute(
                    "INSERT INTO visitors (visitor_qr, total_visits) VALUES (?, 1)",
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


@app.route('/admin/sticker-check', methods=['GET', 'POST'])
def sticker_check():
    """
    Admin endpoint to check if visitor is eligible for sticker
    """
    if request.method == 'GET':
        return render_template('sticker_check.html')

    # Handle POST request
    data = request.get_json()
    visitor_qr = data.get('visitorQR')

    if not visitor_qr:
        return jsonify({'error': 'visitorQR is required'}), 400

    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Get visitor information
            cur.execute(
                "SELECT * FROM visitors WHERE visitor_qr = ?",
                (visitor_qr,)
            )
            visitor = cur.fetchone()

            if not visitor:
                return jsonify({
                    'visitor_qr': visitor_qr,
                    'eligible': False,
                    'total_visits': 0,
                    'message': 'Visitor not found in database'
                }), 404

            # Get detailed visit information
            cur.execute(
                """SELECT team_name, visit_time 
                   FROM visitor_visits 
                   WHERE visitor_qr = ? 
                   ORDER BY visit_time""",
                (visitor_qr,)
            )
            visits = cur.fetchall()

            total_visits = visitor['total_visits']
            eligible = total_visits >= MIN_VISITS_FOR_STICKER
            already_dispensed = visitor['sticker_dispensed']

            visit_list = [{'team': visit['team_name'],
                           'time': visit['visit_time']} for visit in visits]

            return jsonify({
                'visitor_qr': visitor_qr,
                'eligible': eligible and not already_dispensed,
                'total_visits': total_visits,
                'required_visits': MIN_VISITS_FOR_STICKER,
                'visits_remaining': max(0, MIN_VISITS_FOR_STICKER - total_visits),
                'already_dispensed': already_dispensed,
                'sticker_dispensed_time': visitor['sticker_dispensed_time'],
                'visits': visit_list,
                'message': self._get_sticker_message(eligible, already_dispensed, total_visits)
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _get_sticker_message(eligible, already_dispensed, total_visits):
    """Helper function to generate appropriate message"""
    if already_dispensed:
        return "Sticker already dispensed to this visitor"
    elif eligible:
        return "Visitor is eligible for sticker! Ready to dispense."
    else:
        remaining = MIN_VISITS_FOR_STICKER - total_visits
        return f"Visitor needs {remaining} more visits to be eligible for sticker"


@app.route('/admin/dispense-sticker', methods=['POST'])
def dispense_sticker():
    """
    Admin endpoint to mark sticker as dispensed
    """
    data = request.get_json()
    visitor_qr = data.get('visitorQR')
    admin_confirm = data.get('adminConfirm', False)

    if not visitor_qr:
        return jsonify({'error': 'visitorQR is required'}), 400

    if not admin_confirm:
        return jsonify({'error': 'Admin confirmation required'}), 400

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()

            # Check visitor eligibility
            cur.execute(
                "SELECT total_visits, sticker_dispensed FROM visitors WHERE visitor_qr = ?",
                (visitor_qr,)
            )
            visitor = cur.fetchone()

            if not visitor:
                return jsonify({'error': 'Visitor not found'}), 404

            total_visits, already_dispensed = visitor

            if already_dispensed:
                return jsonify({
                    'error': 'Sticker already dispensed to this visitor',
                    'already_dispensed': True
                }), 400

            if total_visits < MIN_VISITS_FOR_STICKER:
                return jsonify({
                    'error': f'Visitor not eligible. Only {total_visits} visits completed.',
                    'eligible': False,
                    'visits_remaining': MIN_VISITS_FOR_STICKER - total_visits
                }), 400

            # Mark sticker as dispensed
            cur.execute(
                """UPDATE visitors 
                   SET sticker_dispensed = TRUE, sticker_dispensed_time = CURRENT_TIMESTAMP 
                   WHERE visitor_qr = ?""",
                (visitor_qr,)
            )
            conn.commit()

            return jsonify({
                'message': 'Sticker dispensed successfully!',
                'visitor_qr': visitor_qr,
                'total_visits': total_visits,
                'dispensed_time': datetime.now().isoformat()
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    """
    Admin dashboard to view statistics
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Get overall statistics
            cur.execute("SELECT COUNT(*) as total_visitors FROM visitors")
            total_visitors = cur.fetchone()['total_visitors']

            cur.execute(
                "SELECT COUNT(*) as eligible_visitors FROM visitors WHERE total_visits >= ?", (MIN_VISITS_FOR_STICKER,))
            eligible_visitors = cur.fetchone()['eligible_visitors']

            cur.execute(
                "SELECT COUNT(*) as stickers_dispensed FROM visitors WHERE sticker_dispensed = TRUE")
            stickers_dispensed = cur.fetchone()['stickers_dispensed']

            cur.execute("SELECT COUNT(*) as total_visits FROM visitor_visits")
            total_visits = cur.fetchone()['total_visits']

            # Get team visit counts
            cur.execute("""
                SELECT team_name, COUNT(*) as visit_count 
                FROM visitor_visits 
                GROUP BY team_name 
                ORDER BY visit_count DESC
            """)
            team_stats = cur.fetchall()

            # Get visitor completion stats
            cur.execute("""
                SELECT total_visits, COUNT(*) as visitor_count 
                FROM visitors 
                GROUP BY total_visits 
                ORDER BY total_visits DESC
            """)
            completion_stats = cur.fetchall()

            return jsonify({
                'summary': {
                    'total_visitors': total_visitors,
                    'eligible_visitors': eligible_visitors,
                    'stickers_dispensed': stickers_dispensed,
                    'total_visits': total_visits,
                    'completion_rate': f"{(eligible_visitors/total_visitors*100):.1f}%" if total_visitors > 0 else "0%"
                },
                'team_stats': [{'team': row['team_name'], 'visits': row['visit_count']} for row in team_stats],
                'completion_stats': [{'visits': row['total_visits'], 'visitors': row['visitor_count']} for row in completion_stats]
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/visitor/status/<visitor_qr>', methods=['GET'])
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


@app.route('/data', methods=['GET'])
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
