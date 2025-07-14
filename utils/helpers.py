"""
Helper functions for the IOT Exhibition application
"""

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
