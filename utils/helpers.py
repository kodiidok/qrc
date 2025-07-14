"""
Helper functions for the IOT Exhibition application
"""
from datetime import datetime
import os
import uuid
import csv
from database import get_db_cursor


def check_qr_code_exists(qr_code: str) -> bool:
    """
    Check if a non-deleted QR code exists in the database.

    Args:
        qr_code (str): The QR code string to check.

    Returns:
        bool: True if exists and not deleted, False otherwise.
    """
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT 1
            FROM qr_codes
            WHERE qr_code = ? AND deleted_time IS NULL
            LIMIT 1
        ''', (qr_code,))
        result = cursor.fetchone()
        return bool(result)


def init_teams_from_csv(csv_path: str) -> dict:
    """
    Initialize the teams table from a CSV file.
    Skips teams that already exist based on team_name.

    Args:
        csv_path (str): Path to the CSV file.

    Returns:
        dict: Summary with created and skipped counts.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found at {csv_path}")

    created = 0
    skipped = 0

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            team_name = row.get('team_name', '').strip()

            if not team_name:
                continue

            with get_db_cursor() as cursor:
                cursor.execute(
                    'SELECT 1 FROM teams WHERE team_name = ?', (team_name,))
                exists = cursor.fetchone()

                if exists:
                    skipped += 1
                    continue

                cursor.execute('''
                    INSERT INTO teams (id, team_name, project_title, description, members, supervisor)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    str(uuid.uuid4()),
                    team_name,
                    row.get('project_title', '').strip(),
                    row.get('description', '').strip(),
                    row.get('members', '').strip(),
                    row.get('supervisor', '').strip()
                ))
                created += 1

    return {"teams_created": created, "teams_skipped": skipped}


def record_visitor_visit(qr_code: str, team_id: str) -> dict:
    """
    Records a visit for a visitor to a team.
    Updates both visitor_visits and visitors table.

    Returns:
        dict: {
            'recorded': True/False,
            'visitor_created': True/False,
            'already_visited': True/False
        }
    """
    from uuid import UUID
    try:
        UUID(team_id)  # Validate UUID
    except ValueError:
        return {"recorded": False, "error": "Invalid team_id"}

    result = {
        "recorded": False,
        "visitor_created": False,
        "already_visited": False
    }

    now = datetime.utcnow().isoformat()

    with get_db_cursor() as cursor:
        # Lookup team name
        cursor.execute("SELECT team_name FROM teams WHERE id = ?", (team_id,))
        team_row = cursor.fetchone()
        if not team_row:
            return {"recorded": False, "error": "Team not found"}

        team_name = team_row["team_name"]

        # Check if already visited this team
        cursor.execute('''
            SELECT 1 FROM visitor_visits
            WHERE visitor_qr = ? AND team_name = ?
        ''', (qr_code, team_name))

        if cursor.fetchone():
            result['already_visited'] = True
            return result  # No duplicate insert

        # Insert into visitor_visits
        cursor.execute('''
            INSERT INTO visitor_visits (visitor_qr, team_name, visit_time)
            VALUES (?, ?, ?)
        ''', (qr_code, team_name, now))

        result['recorded'] = True

        # Check if visitor exists
        cursor.execute(
            "SELECT * FROM visitors WHERE visitor_qr = ?", (qr_code,))
        visitor_row = cursor.fetchone()

        if visitor_row:
            # Update total_visits and last_visit
            total = visitor_row["total_visits"] or 0
            cursor.execute('''
                UPDATE visitors
                SET total_visits = ?, last_visit = ?
                WHERE visitor_qr = ?
            ''', (total + 1, now, qr_code))
        else:
            # Insert new visitor
            cursor.execute('''
                INSERT INTO visitors (visitor_qr, first_visit, last_visit, total_visits)
                VALUES (?, ?, ?, ?)
            ''', (qr_code, now, now, 1))
            result['visitor_created'] = True

    return result
