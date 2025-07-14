"""
Database models for the IOT Exhibition application
"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from config import Config
from .database import get_db_connection


class VisitorVisit:
    """Model for visitor visits to teams"""

    def __init__(self, visitor_qr: str, team_name: str, visit_time: str = None, visit_id: int = None):
        self.id = visit_id
        self.visitor_qr = visitor_qr
        self.team_name = team_name
        self.visit_time = visit_time

    @classmethod
    def create_visit(cls, visitor_qr: str, team_name: str) -> Dict[str, Any]:
        """
        Create a new visit record
        Returns dictionary with visit information and status
        """
        if team_name not in Config.ALLOWED_TEAMS:
            raise ValueError(
                f'Invalid team name. Allowed teams: {", ".join(Config.ALLOWED_TEAMS)}')

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if visitor already visited this team
            cursor.execute(
                "SELECT id FROM visitor_visits WHERE visitor_qr = ? AND team_name = ?",
                (visitor_qr, team_name)
            )
            existing_visit = cursor.fetchone()

            if existing_visit:
                return {
                    'message': f'Visitor has already visited {team_name}',
                    'duplicate': True,
                    'visit_id': existing_visit['id']
                }

            # Insert new visit record
            cursor.execute(
                "INSERT INTO visitor_visits (visitor_qr, team_name) VALUES (?, ?)",
                (visitor_qr, team_name)
            )
            visit_id = cursor.lastrowid

            # Update visitor summary
            visitor = Visitor.get_by_qr(visitor_qr)
            if visitor:
                new_total = visitor.total_visits + 1
                Visitor.update_visit_count(visitor_qr, new_total)
            else:
                # Create new visitor record
                Visitor.create_visitor(visitor_qr, total_visits=1)
                new_total = 1

            conn.commit()

            return {
                'message': f'Visit to {team_name} recorded successfully',
                'visit_id': visit_id,
                'total_visits': new_total,
                'visits_remaining': max(0, Config.MIN_VISITS_FOR_STICKER - new_total),
                'eligible_for_sticker': new_total >= Config.MIN_VISITS_FOR_STICKER
            }

    @classmethod
    def get_visits_by_visitor(cls, visitor_qr: str) -> List['VisitorVisit']:
        """Get all visits for a specific visitor"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM visitor_visits WHERE visitor_qr = ? ORDER BY visit_time",
                (visitor_qr,)
            )
            rows = cursor.fetchall()

            return [cls(
                visitor_qr=row['visitor_qr'],
                team_name=row['team_name'],
                visit_time=row['visit_time'],
                visit_id=row['id']
            ) for row in rows]

    @classmethod
    def get_team_visit_stats(cls) -> List[Dict[str, Any]]:
        """Get visit statistics by team"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT team_name, COUNT(*) as visit_count 
                FROM visitor_visits 
                GROUP BY team_name 
                ORDER BY visit_count DESC
            """)

            return [{'team': row['team_name'], 'visits': row['visit_count']}
                    for row in cursor.fetchall()]


class Visitor:
    """Model for visitors"""

    def __init__(self, visitor_qr: str, qr_code_image: str = None, total_visits: int = 0,
                 sticker_dispensed: bool = False, sticker_dispensed_time: str = None,
                 first_visit: str = None, last_visit: str = None, is_active: bool = True):
        self.visitor_qr = visitor_qr
        self.qr_code_image = qr_code_image
        self.total_visits = total_visits
        self.sticker_dispensed = sticker_dispensed
        self.sticker_dispensed_time = sticker_dispensed_time
        self.first_visit = first_visit
        self.last_visit = last_visit
        self.is_active = is_active

    @classmethod
    def create_visitor(cls, visitor_qr: str, qr_code_image: str = None, total_visits: int = 0):
        """Create a new visitor record"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO visitors (visitor_qr, qr_code_image, total_visits, first_visit, last_visit) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (visitor_qr, qr_code_image, total_visits))
            conn.commit()

    @classmethod
    def get_by_qr(cls, visitor_qr: str) -> Optional['Visitor']:
        """Get visitor by QR code"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM visitors WHERE visitor_qr = ?", (visitor_qr,))
            row = cursor.fetchone()

            if row:
                return cls(
                    visitor_qr=row['visitor_qr'],
                    qr_code_image=row['qr_code_image'],
                    total_visits=row['total_visits'],
                    sticker_dispensed=row['sticker_dispensed'],
                    sticker_dispensed_time=row['sticker_dispensed_time'],
                    first_visit=row['first_visit'],
                    last_visit=row['last_visit'],
                    is_active=row['is_active']
                )
            return None

    @classmethod
    def update_visit_count(cls, visitor_qr: str, new_total: int):
        """Update visitor's visit count"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE visitors 
                SET total_visits = ?, 
                    last_visit = CURRENT_TIMESTAMP,
                    first_visit = COALESCE(first_visit, CURRENT_TIMESTAMP)
                WHERE visitor_qr = ?
            """, (new_total, visitor_qr))
            conn.commit()

    @classmethod
    def dispense_sticker(cls, visitor_qr: str) -> Dict[str, Any]:
        """Mark sticker as dispensed for visitor"""
        visitor = cls.get_by_qr(visitor_qr)

        if not visitor:
            return {'error': 'Visitor not found', 'success': False}

        if visitor.sticker_dispensed:
            return {
                'error': 'Sticker already dispensed to this visitor',
                'success': False,
                'already_dispensed': True
            }

        if visitor.total_visits < Config.MIN_VISITS_FOR_STICKER:
            return {
                'error': f'Visitor not eligible. Only {visitor.total_visits} visits completed.',
                'success': False,
                'eligible': False,
                'visits_remaining': Config.MIN_VISITS_FOR_STICKER - visitor.total_visits
            }

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE visitors 
                SET sticker_dispensed = TRUE, sticker_dispensed_time = CURRENT_TIMESTAMP 
                WHERE visitor_qr = ?
            """, (visitor_qr,))
            conn.commit()

        return {
            'message': 'Sticker dispensed successfully!',
            'success': True,
            'visitor_qr': visitor_qr,
            'total_visits': visitor.total_visits,
            'dispensed_time': datetime.now().isoformat()
        }

    @classmethod
    def get_visitor_status(cls, visitor_qr: str) -> Dict[str, Any]:
        """Get comprehensive visitor status"""
        visitor = cls.get_by_qr(visitor_qr)

        if not visitor:
            return {
                'visitor_qr': visitor_qr,
                'found': False,
                'message': 'Visitor not found'
            }

        # Get visited teams
        visits = VisitorVisit.get_visits_by_visitor(visitor_qr)
        visited_teams = [visit.team_name for visit in visits]
        not_visited_teams = [
            team for team in Config.ALLOWED_TEAMS if team not in visited_teams]

        return {
            'visitor_qr': visitor_qr,
            'found': True,
            'total_visits': visitor.total_visits,
            'required_visits': Config.MIN_VISITS_FOR_STICKER,
            'visits_remaining': max(0, Config.MIN_VISITS_FOR_STICKER - visitor.total_visits),
            'eligible_for_sticker': visitor.total_visits >= Config.MIN_VISITS_FOR_STICKER,
            'sticker_dispensed': visitor.sticker_dispensed,
            'visited_teams': visited_teams,
            'not_visited_teams': not_visited_teams,
            'progress_percentage': (visitor.total_visits / Config.MIN_VISITS_FOR_STICKER) * 100,
            'visits': [{'team': visit.team_name, 'time': visit.visit_time} for visit in visits]
        }

    @classmethod
    def get_completion_stats(cls) -> List[Dict[str, Any]]:
        """Get visitor completion statistics"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT total_visits, COUNT(*) as visitor_count 
                FROM visitors 
                WHERE total_visits > 0
                GROUP BY total_visits 
                ORDER BY total_visits DESC
            """)

            return [{'visits': row['total_visits'], 'visitors': row['visitor_count']}
                    for row in cursor.fetchall()]


class QRCode:
    """Model for QR codes"""

    def __init__(self, qr_code: str, qr_image_base64: str = None, is_printed: bool = False,
                 is_distributed: bool = False, notes: str = None, code_id: int = None):
        self.id = code_id
        self.qr_code = qr_code
        self.qr_image_base64 = qr_image_base64
        self.is_printed = is_printed
        self.is_distributed = is_distributed
        self.notes = notes

    @classmethod
    def create_qr_code(cls, qr_code: str, qr_image_base64: str):
        """Create a new QR code record"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO qr_codes (qr_code, qr_image_base64) 
                VALUES (?, ?)
            """, (qr_code, qr_image_base64))

            # Also create visitor record
            cursor.execute("""
                INSERT INTO visitors (visitor_qr, qr_code_image) 
                VALUES (?, ?)
            """, (qr_code, qr_image_base64))

            conn.commit()
            return cursor.lastrowid

    @classmethod
    def get_paginated_codes(cls, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get paginated QR codes with visitor information"""
        offset = (page - 1) * per_page

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get total count
            cursor.execute("SELECT COUNT(*) as total FROM qr_codes")
            total_codes = cursor.fetchone()['total']

            # Get paginated results
            cursor.execute("""
                SELECT qc.*, v.total_visits, v.sticker_dispensed, v.first_visit, v.last_visit
                FROM qr_codes qc
                LEFT JOIN visitors v ON qc.qr_code = v.visitor_qr
                ORDER BY qc.generated_time DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))

            codes = cursor.fetchall()

            code_list = []
            for code in codes:
                code_list.append({
                    'id': code['id'],
                    'qr_code': code['qr_code'],
                    'generated_time': code['generated_time'],
                    'is_printed': code['is_printed'],
                    'is_distributed': code['is_distributed'],
                    'total_visits': code['total_visits'] or 0,
                    'sticker_dispensed': code['sticker_dispensed'] or False,
                    'first_visit': code['first_visit'],
                    'last_visit': code['last_visit'],
                    'status': 'used' if code['total_visits'] and code['total_visits'] > 0 else 'unused'
                })

            return {
                'total_codes': total_codes,
                'page': page,
                'per_page': per_page,
                'total_pages': (total_codes + per_page - 1) // per_page,
                'codes': code_list
            }

    @classmethod
    def get_by_code(cls, qr_code: str) -> Optional['QRCode']:
        """Get QR code by code string"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM qr_codes WHERE qr_code = ?", (qr_code,))
            row = cursor.fetchone()

            if row:
                return cls(
                    qr_code=row['qr_code'],
                    qr_image_base64=row['qr_image_base64'],
                    is_printed=row['is_printed'],
                    is_distributed=row['is_distributed'],
                    notes=row['notes'],
                    code_id=row['id']
                )
            return None

    @classmethod
    def mark_printed(cls, qr_codes: List[str]) -> int:
        """Mark QR codes as printed"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in qr_codes])
            cursor.execute(f"""
                UPDATE qr_codes 
                SET is_printed = TRUE 
                WHERE qr_code IN ({placeholders})
            """, qr_codes)
            conn.commit()
            return cursor.rowcount

    @classmethod
    def mark_distributed(cls, qr_codes: List[str]) -> int:
        """Mark QR codes as distributed"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in qr_codes])
            cursor.execute(f"""
                UPDATE qr_codes 
                SET is_distributed = TRUE 
                WHERE qr_code IN ({placeholders})
            """, qr_codes)
            conn.commit()
            return cursor.rowcount

    @classmethod
    def get_all_for_export(cls) -> List[Dict[str, str]]:
        """Get all QR codes for export/printing"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT qr_code, qr_image_base64 
                FROM qr_codes 
                ORDER BY generated_time
            """)

            return [{'qr_code': row['qr_code'], 'qr_image_base64': row['qr_image_base64']}
                    for row in cursor.fetchall()]
