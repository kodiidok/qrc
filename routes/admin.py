from flask import Blueprint, request, jsonify, render_template
import sqlite3
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

# Minimum visits required for sticker eligibility
MIN_VISITS_FOR_STICKER = 11

DB_NAME = 'exhibition-database.db'


@admin_bp.route('/admin/sticker-check', methods=['GET', 'POST'])
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
                'message': _get_sticker_message(eligible, already_dispensed, total_visits)
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


@admin_bp.route('/admin/dispense-sticker', methods=['POST'])
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


@admin_bp.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    """
    Admin dashboard to view statistics
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Get overall statistics
            cur.execute("SELECT COUNT(*) as total_generated FROM qr_codes")
            total_generated = cur.fetchone()['total_generated']

            cur.execute(
                "SELECT COUNT(*) as total_visitors FROM visitors WHERE total_visits > 0")
            total_active_visitors = cur.fetchone()['total_visitors']

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
                    'total_qr_codes_generated': total_generated,
                    'total_visitors': total_visitors,
                    'active_visitors': total_active_visitors,
                    'eligible_visitors': eligible_visitors,
                    'stickers_dispensed': stickers_dispensed,
                    'total_visits': total_visits,
                    'usage_rate': f"{(total_active_visitors/total_generated*100):.1f}%" if total_generated > 0 else "0%",
                    'completion_rate': f"{(eligible_visitors/total_active_visitors*100):.1f}%" if total_active_visitors > 0 else "0%"
                },
                'team_stats': [{'team': row['team_name'], 'visits': row['visit_count']} for row in team_stats],
                'completion_stats': [{'visits': row['total_visits'], 'visitors': row['visitor_count']} for row in completion_stats]
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
