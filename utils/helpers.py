"""
Helper functions for the IOT Exhibition application
"""
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
