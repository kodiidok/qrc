"""
Helper functions for the IOT Exhibition application
"""

import socket
from typing import Dict, Any, Optional
from config import Config


def get_sticker_message(eligible: bool, already_dispensed: bool, total_visits: int) -> str:
    """
    Generate appropriate sticker eligibility message

    Args:
        eligible: Whether visitor is eligible for sticker
        already_dispensed: Whether sticker was already dispensed
        total_visits: Current number of visits

    Returns:
        Appropriate message string
    """
    if already_dispensed:
        return "Sticker already dispensed to this visitor"
    elif eligible:
        return "Visitor is eligible for sticker! Ready to dispense."
    else:
        remaining = Config.MIN_VISITS_FOR_STICKER - total_visits
        return f"Visitor needs {remaining} more visits to be eligible for sticker"


def validate_team_name(team_name: str) -> Dict[str, Any]:
    """
    Validate team name against allowed teams

    Args:
        team_name: Team name to validate

    Returns:
        Dictionary with validation result
    """
    if not team_name:
        return {
            'valid': False,
            'error': 'Team name is required'
        }

    if team_name not in Config.ALLOWED_TEAMS:
        return {
            'valid': False,
            'error': f'Invalid team name. Allowed teams: {", ".join(Config.ALLOWED_TEAMS)}'
        }

    return {
        'valid': True,
        'team_name': team_name
    }


def get_network_ip() -> Optional[str]:
    """
    Get the local network IP address

    Returns:
        Local IP address or None if unable to determine
    """
    try:
        # Create a socket and connect to a remote address
        # This doesn't actually send data, just determines the local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return None


def format_visit_time(visit_time: str) -> str:
    """
    Format visit time for display

    Args:
        visit_time: ISO format timestamp string

    Returns:
        Formatted time string
    """
    from datetime import datetime

    if not visit_time:
        return "Unknown"

    try:
        # Parse the timestamp
        dt = datetime.fromisoformat(visit_time.replace('Z', '+00:00'))

        # Format as readable string
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return visit_time


def calculate_progress_percentage(total_visits: int, required_visits: int = None) -> float:
    """
    Calculate progress percentage towards sticker eligibility

    Args:
        total_visits: Number of visits completed
        required_visits: Required visits for sticker (defaults to config value)

    Returns:
        Progress percentage (0-100)
    """
    if required_visits is None:
        required_visits = Config.MIN_VISITS_FOR_STICKER

    if required_visits == 0:
        return 100.0

    percentage = (total_visits / required_visits) * 100
    return min(percentage, 100.0)  # Cap at 100%


def get_visitor_status_summary(total_visits: int, sticker_dispensed: bool) -> Dict[str, Any]:
    """
    Get a summary of visitor status

    Args:
        total_visits: Number of visits completed
        sticker_dispensed: Whether sticker was dispensed

    Returns:
        Dictionary with status summary
    """
    eligible = total_visits >= Config.MIN_VISITS_FOR_STICKER
    visits_remaining = max(0, Config.MIN_VISITS_FOR_STICKER - total_visits)
    progress = calculate_progress_percentage(total_visits)

    if sticker_dispensed:
        status = "completed"
        message = "Sticker dispensed - Exhibition completed!"
    elif eligible:
        status = "eligible"
        message = "Eligible for sticker"
    elif total_visits > 0:
        status = "in_progress"
        message = f"{visits_remaining} more visits needed"
    else:
        status = "not_started"
        message = "No visits recorded"

    return {
        'status': status,
        'message': message,
        'progress_percentage': progress,
        'visits_remaining': visits_remaining,
        'eligible': eligible,
        'completed': sticker_dispensed
    }


def sanitize_qr_code(qr_code: str) -> str:
    """
    Sanitize QR code input

    Args:
        qr_code: Raw QR code input

    Returns:
        Sanitized QR code string
    """
    if not qr_code:
        return ""

    # Strip whitespace and convert to upper case
    sanitized = qr_code.strip().upper()

    # Remove any non-alphanumeric characters except underscores
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '_')

    return sanitized


def validate_admin_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate admin request data

    Args:
        data: Request data dictionary

    Returns:
        Dictionary with validation result
    """
    visitor_qr = data.get('visitorQR')
    admin_confirm = data.get('adminConfirm', False)

    if not visitor_qr:
        return {
            'valid': False,
            'error': 'visitorQR is required'
        }

    if not admin_confirm:
        return {
            'valid': False,
            'error': 'Admin confirmation required'
        }

    return {
        'valid': True,
        'visitor_qr': sanitize_qr_code(visitor_qr)
    }


def get_team_display_name(team_name: str) -> str:
    """
    Get display name for team

    Args:
        team_name: Internal team name

    Returns:
        Display-friendly team name
    """
    if not team_name:
        return "Unknown Team"

    # Convert team1 -> Team 1, team2 -> Team 2, etc.
    if team_name.startswith('team') and team_name[4:].isdigit():
        team_number = team_name[4:]
        return f"Team {team_number}"

    return team_name.title()


def create_response_dict(success: bool, message: str = None, data: Dict[str, Any] = None,
                         error: str = None, status_code: int = 200) -> tuple:
    """
    Create standardized response dictionary

    Args:
        success: Whether the operation was successful
        message: Success message
        data: Additional data to include
        error: Error message
        status_code: HTTP status code

    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        'success': success,
        'timestamp': datetime.now().isoformat()
    }

    if success:
        if message:
            response['message'] = message
        if data:
            response.update(data)
    else:
        response['error'] = error or 'An error occurred'

    return response, status_code


def get_exhibition_stats_summary() -> Dict[str, Any]:
    """
    Get summary statistics for the exhibition

    Returns:
        Dictionary with exhibition statistics
    """
    from database.database import get_db_connection

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get basic counts
        cursor.execute("SELECT COUNT(*) as count FROM qr_codes")
        total_generated = cursor.fetchone()['count']

        cursor.execute(
            "SELECT COUNT(*) as count FROM visitors WHERE total_visits > 0")
        active_visitors = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM visitors WHERE total_visits >= ?",
                       (Config.MIN_VISITS_FOR_STICKER,))
        eligible_visitors = cursor.fetchone()['count']

        cursor.execute(
            "SELECT COUNT(*) as count FROM visitors WHERE sticker_dispensed = TRUE")
        stickers_dispensed = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM visitor_visits")
        total_visits = cursor.fetchone()['count']

        # Calculate rates
        usage_rate = (active_visitors / total_generated *
                      100) if total_generated > 0 else 0
        completion_rate = (eligible_visitors / active_visitors *
                           100) if active_visitors > 0 else 0

        return {
            'total_qr_codes': total_generated,
            'active_visitors': active_visitors,
            'eligible_visitors': eligible_visitors,
            'stickers_dispensed': stickers_dispensed,
            'total_visits': total_visits,
            'usage_rate': f"{usage_rate:.1f}%",
            'completion_rate': f"{completion_rate:.1f}%"
        }


def validate_pagination_params(page: int, per_page: int) -> Dict[str, Any]:
    """
    Validate pagination parameters

    Args:
        page: Page number
        per_page: Items per page

    Returns:
        Dictionary with validated parameters
    """
    # Ensure page is at least 1
    page = max(1, page)

    # Ensure per_page is within allowed range
    per_page = max(1, min(per_page, Config.MAX_PAGE_SIZE))

    return {
        'page': page,
        'per_page': per_page,
        'offset': (page - 1) * per_page
    }
