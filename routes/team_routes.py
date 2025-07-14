from flask import Blueprint, render_template, abort
from database import get_db_cursor

team_bp = Blueprint('team', __name__, url_prefix='/team')


@team_bp.route('/<team_id>/scan-qr')
def team_scan_qr(team_id):
    # Verify team exists
    with get_db_cursor() as cursor:
        cursor.execute('SELECT team_name FROM teams WHERE id = ?', (team_id,))
        team = cursor.fetchone()

    if not team:
        abort(404, description="Team not found")

    return render_template('team_scan_qr.html', team_id=team_id, team_name=team['team_name'])
