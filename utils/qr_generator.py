"""
QR Code Generation Utilities
"""

import qrcode
import base64
from datetime import datetime, timezone
from io import BytesIO
from config import Config
from database import get_db_cursor


class QRGenerator:
    @staticmethod
    def generate_qr_base64(data):
        """
        Generate a base64-encoded QR code image from input data
        """
        qr = qrcode.QRCode(
            version=Config.QR_CODE_VERSION,
            box_size=Config.QR_CODE_BOX_SIZE,
            border=Config.QR_CODE_BORDER,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color=Config.QR_CODE_FILL_COLOR,
                            back_color=Config.QR_CODE_BACK_COLOR)

        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    @staticmethod
    def init_qr_codes():
        """
        Populate the qr_codes table with generated QR code data
        """
        default_count = Config.DEFAULT_QR_CODE_COUNT

        with get_db_cursor() as cursor:
            for i in range(default_count):
                qr_code_text = f"QR_{i + 1:04}"
                qr_base64 = QRGenerator.generate_qr_base64(qr_code_text)

                cursor.execute('''
                    INSERT INTO qr_codes (qr_code, qr_image_base64)
                    VALUES (?, ?)
                ''', (qr_code_text, qr_base64))

    @staticmethod
    def reset_qr_codes():
        """
        Soft delete all existing QR codes by:
        - Setting deleted_time to now
        - Prefixing qr_code with 'DEL_' to avoid naming conflicts

        Then insert new QR codes starting fresh.
        """
        now = datetime.now(timezone.utc).isoformat()

        with get_db_cursor() as cursor:
            # Prefix qr_code and set deleted_time only for active (non-deleted) rows
            cursor.execute('''
                UPDATE qr_codes
                SET 
                    qr_code = 'DEL_' || qr_code,
                    deleted_time = ?
                WHERE deleted_time IS NULL
            ''', (now,))

        QRGenerator.init_qr_codes()
