"""
Database connection and initialization utilities
"""

import sqlite3
from contextlib import contextmanager
from config import Config


def get_db_connection():
    """
    Get a database connection with row factory
    """
    conn = sqlite3.connect(Config.DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db_cursor():
    """
    Context manager for database operations
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    """
    Initialize the database with required tables
    """
    with sqlite3.connect(Config.DB_NAME) as conn:
        # Create visitor_visits table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS visitor_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_qr TEXT NOT NULL,
                team_name TEXT NOT NULL,
                visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(visitor_qr, team_name)
            )
        ''')

        # Create visitors table with generated QR codes
        conn.execute('''
            CREATE TABLE IF NOT EXISTS visitors (
                visitor_qr TEXT PRIMARY KEY,
                qr_code_image TEXT,
                generated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                first_visit TIMESTAMP,
                last_visit TIMESTAMP,
                total_visits INTEGER DEFAULT 0,
                sticker_dispensed BOOLEAN DEFAULT FALSE,
                sticker_dispensed_time TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')

        # Create QR codes table for better organization
        conn.execute('''
            CREATE TABLE IF NOT EXISTS qr_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qr_code TEXT UNIQUE NOT NULL,
                qr_image_base64 TEXT,
                generated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_printed BOOLEAN DEFAULT FALSE,
                is_distributed BOOLEAN DEFAULT FALSE,
                deleted_time TIMESTAMP NULL DEFAULT NULL,
                notes TEXT
            )
        ''')

        # Create indexes for better performance
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_visitor_visits_visitor_qr 
            ON visitor_visits(visitor_qr)
        ''')

        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_visitor_visits_team_name 
            ON visitor_visits(team_name)
        ''')

        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_visitors_total_visits 
            ON visitors(total_visits)
        ''')

        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_visitors_sticker_dispensed 
            ON visitors(sticker_dispensed)
        ''')

        conn.commit()


def reset_db():
    """
    Drop all tables and recreate them (use with caution)
    """
    with sqlite3.connect(Config.DB_NAME) as conn:
        # Drop tables
        conn.execute('DROP TABLE IF EXISTS visitor_visits')
        conn.execute('DROP TABLE IF EXISTS visitors')
        conn.execute('DROP TABLE IF EXISTS qr_codes')
        conn.commit()

    # Recreate tables
    init_db()


def get_db_stats():
    """
    Get basic database statistics
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get table counts
        cursor.execute("SELECT COUNT(*) as count FROM visitor_visits")
        visits_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM visitors")
        visitors_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM qr_codes")
        qr_codes_count = cursor.fetchone()['count']

        return {
            'visitor_visits': visits_count,
            'visitors': visitors_count,
            'qr_codes': qr_codes_count
        }
