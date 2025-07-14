"""
QR Code Generation Utilities
"""

import qrcode
import csv
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

    @staticmethod
    def export_active_qr_codes_to_csv(csv_path='active_qr_codes.csv'):
        """
        Retrieve all non-deleted QR codes and save them to a CSV file.

        :param csv_path: Path to save the CSV file
        :return: Path to the generated CSV file
        """
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT qr_code, qr_image_base64, generated_time, is_printed, is_distributed, notes
                FROM qr_codes
                WHERE deleted_time IS NULL
                ORDER BY id
            ''')
            rows = cursor.fetchall()

        # Define CSV headers matching selected columns
        headers = ['qr_code', 'qr_image_base64', 'generated_time',
                   'is_printed', 'is_distributed', 'notes']

        with open(csv_path, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([row[h] for h in headers])

        return csv_path
