from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime
import socket

app = Flask(__name__)
DB_NAME = 'qr-database.db'

# Define allowed team names
ALLOWED_TEAMS = ['teamA', 'teamB', 'teamC', 'teamD']

# Ensure table exists
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qr_data TEXT NOT NULL,
                team_name TEXT NOT NULL,
                scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
init_db()

@app.route('/scan/<team_name>', methods=['GET', 'POST'])
def scan(team_name):
    # Validate team name
    if team_name not in ALLOWED_TEAMS:
        return jsonify({'error': f'Invalid team name. Allowed teams: {", ".join(ALLOWED_TEAMS)}'}), 400
    
    if request.method == 'GET':
        return render_template('scan_form.html', team_name=team_name)
    
    # Handle POST request
    data = request.get_json()
    qr_data = data.get('qrData')
    print(f"Team: {team_name}, QR Data: {qr_data}")

    if not qr_data:
        return jsonify({'error': 'qrData is required'}), 400

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            
            # Check if QR data already exists for this team
            cur.execute("SELECT id FROM scans WHERE qr_data = ? AND team_name = ?", (qr_data, team_name))
            existing_record = cur.fetchone()
            
            if existing_record:
                return jsonify({'message': f'QR data already exists in database for team {team_name}', 'id': existing_record[0]}), 200
            
            # Insert new QR data if it doesn't exist for this team
            cur.execute("INSERT INTO scans (qr_data, team_name) VALUES (?, ?)", (qr_data, team_name))
            conn.commit()
            return jsonify({'id': cur.lastrowid, 'message': f'QR data added successfully for team {team_name}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/data', methods=['GET'])
def get_data():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM scans ORDER BY scan_time DESC").fetchall()
            html = "<h1>QR Scans</h1><ul>"
            for row in rows:
                html += f"<li>ID: {row['id']} | Team: {row['team_name']} | Data: {row['qr_data']} | Time: {row['scan_time']}</li>"
            html += "</ul>"
            return html
    except Exception as e:
        return str(e), 500

@app.route('/report/duplicates/<int:min_count>', methods=['GET'])
def report_duplicates(min_count):
    """
    Get a report of QR data that appears more than min_count times in the database
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            
            # Query to find QR data that appears more than min_count times
            query = """
                SELECT qr_data, COUNT(*) as scan_count, 
                       GROUP_CONCAT(team_name) as teams,
                       GROUP_CONCAT(scan_time) as scan_times
                FROM scans 
                GROUP BY qr_data 
                HAVING COUNT(*) >= ?
                ORDER BY scan_count DESC, qr_data
            """
            
            rows = conn.execute(query, (min_count,)).fetchall()
            
            if not rows:
                return jsonify({
                    'message': f'No QR data found that appears {min_count} or more times',
                    'min_count': min_count,
                    'duplicates': []
                })
            
            # Format the results
            duplicates = []
            for row in rows:
                teams_list = row['teams'].split(',') if row['teams'] else []
                scan_times_list = row['scan_times'].split(',') if row['scan_times'] else []
                
                duplicates.append({
                    'qr_data': row['qr_data'],
                    'scan_count': row['scan_count'],
                    'teams': teams_list,
                    'scan_times': scan_times_list
                })
            
            return jsonify({
                'message': f'Found {len(duplicates)} QR data items that appear {min_count} or more times',
                'min_count': min_count,
                'duplicates': duplicates
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/report/duplicates', methods=['GET'])
def report_duplicates_default():
    """
    Default route for duplicates report (minimum 2 times)
    """
    return report_duplicates(2)

@app.route('/check-qr', methods=['GET', 'POST'])
def check_qr():
    """
    Route to scan QR code and check how many times it appears in database
    """
    if request.method == 'GET':
        return render_template('check_qr.html')
    
    # Handle POST request
    data = request.get_json()
    qr_data = data.get('qrData')
    
    if not qr_data:
        return jsonify({'error': 'qrData is required'}), 400

    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get all scans for this QR data from all teams
            query = """
                SELECT id, team_name, scan_time 
                FROM scans 
                WHERE qr_data = ? 
                ORDER BY scan_time DESC
            """
            
            rows = conn.execute(query, (qr_data,)).fetchall()
            
            if not rows:
                return jsonify({
                    'qr_data': qr_data,
                    'scan_count': 0,
                    'message': 'This QR code has not been scanned before',
                    'scans': [],
                    'is_valid': False
                })
            
            # Format the results
            scans = []
            for row in rows:
                scans.append({
                    'id': row['id'],
                    'team_name': row['team_name'],
                    'scan_time': row['scan_time']
                })
            
            scan_count = len(scans)
            is_valid = scan_count >= 3
            
            return jsonify({
                'qr_data': qr_data,
                'scan_count': scan_count,
                'message': f'This QR code has been scanned {scan_count} time(s)',
                'scans': scans,
                'is_valid': is_valid
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500




if __name__ == '__main__':
    app.run( port=5000)
