"""
QR Code generation utilities for the IOT Exhibition application
"""

import qrcode
import io
import base64
import random
import string
from datetime import datetime
from typing import List, Dict, Any, Set
from config import Config
from database.models import QRCode


class QRCodeGenerator:
    """QR Code generation and management utility"""

    def __init__(self):
        self.config = Config()

    def generate_unique_qr_code(self) -> str:
        """Generate a unique QR code string"""
        timestamp = str(int(datetime.now().timestamp()))
        random_string = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=8))
        return f"VISITOR_{timestamp}_{random_string}"

    def create_qr_image(self, qr_code_text: str) -> str:
        """
        Create QR code image and return as base64 string

        Args:
            qr_code_text: The text to encode in the QR code

        Returns:
            Base64 encoded PNG image string
        """
        qr = qrcode.QRCode(
            version=Config.QR_CODE_VERSION,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=Config.QR_CODE_BOX_SIZE,
            border=Config.QR_CODE_BORDER,
        )
        qr.add_data(qr_code_text)
        qr.make(fit=True)

        # Create QR code image
        qr_image = qr.make_image(
            fill_color=Config.QR_CODE_FILL_COLOR,
            back_color=Config.QR_CODE_BACK_COLOR
        )

        # Convert to base64 for storage
        img_buffer = io.BytesIO()
        qr_image.save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()

        return img_base64

    def generate_batch_qr_codes(self, count: int = Config.DEFAULT_QR_CODE_COUNT) -> Dict[str, Any]:
        """
        Generate a batch of unique QR codes

        Args:
            count: Number of QR codes to generate

        Returns:
            Dictionary with generation results
        """
        if count > Config.MAX_QR_CODES_PER_BATCH:
            raise ValueError(
                f'Maximum {Config.MAX_QR_CODES_PER_BATCH} QR codes can be generated at once')

        generated_codes = []
        existing_codes = self._get_existing_codes()

        # Generate unique QR codes
        attempts = 0
        max_attempts = count * 3  # Prevent infinite loops

        while len(generated_codes) < count and attempts < max_attempts:
            qr_code_text = self.generate_unique_qr_code()
            attempts += 1

            if qr_code_text not in existing_codes:
                try:
                    # Generate QR code image
                    img_base64 = self.create_qr_image(qr_code_text)

                    # Store in database
                    QRCode.create_qr_code(qr_code_text, img_base64)

                    generated_codes.append({
                        'qr_code': qr_code_text,
                        'qr_image': img_base64
                    })
                    existing_codes.add(qr_code_text)

                except Exception as e:
                    # Log error but continue generating
                    print(f"Error generating QR code {qr_code_text}: {str(e)}")
                    continue

        if len(generated_codes) < count:
            return {
                'success': False,
                'error': f'Could only generate {len(generated_codes)} unique codes out of {count} requested',
                'generated_count': len(generated_codes)
            }

        return {
            'success': True,
            'message': f'Successfully generated {len(generated_codes)} QR codes',
            'generated_count': len(generated_codes),
            # Show first 10 as sample
            'codes': [code['qr_code'] for code in generated_codes[:10]]
        }

    def _get_existing_codes(self) -> Set[str]:
        """Get set of existing QR codes to avoid duplicates"""
        from database.database import get_db_connection

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT qr_code FROM qr_codes")
            return {row['qr_code'] for row in cursor.fetchall()}

    def validate_qr_code(self, qr_code: str) -> bool:
        """
        Validate QR code format

        Args:
            qr_code: QR code string to validate

        Returns:
            True if valid, False otherwise
        """
        if not qr_code:
            return False

        # Check if it starts with VISITOR_ and has the expected format
        if not qr_code.startswith('VISITOR_'):
            return False

        # Split and check parts
        parts = qr_code.split('_')
        if len(parts) != 3:
            return False

        # Check timestamp part (should be numeric)
        try:
            int(parts[1])
        except ValueError:
            return False

        # Check random string part (should be alphanumeric)
        if not parts[2].isalnum():
            return False

        return True

    def get_qr_code_info(self, qr_code: str) -> Dict[str, Any]:
        """
        Get information about a QR code

        Args:
            qr_code: QR code string

        Returns:
            Dictionary with QR code information
        """
        if not self.validate_qr_code(qr_code):
            return {
                'valid': False,
                'error': 'Invalid QR code format'
            }

        # Extract timestamp from QR code
        parts = qr_code.split('_')
        timestamp = int(parts[1])
        generation_time = datetime.fromtimestamp(timestamp)

        # Get QR code from database
        qr_code_obj = QRCode.get_by_code(qr_code)

        return {
            'valid': True,
            'qr_code': qr_code,
            'generation_time': generation_time.isoformat(),
            'exists_in_db': qr_code_obj is not None,
            'is_printed': qr_code_obj.is_printed if qr_code_obj else False,
            'is_distributed': qr_code_obj.is_distributed if qr_code_obj else False
        }

    def generate_export_html(self, codes: List[Dict[str, str]]) -> str:
        """
        Generate HTML page with QR codes for printing

        Args:
            codes: List of dictionaries with 'qr_code' and 'qr_image_base64' keys

        Returns:
            HTML string for printing
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>QR Codes for Printing</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 20px; 
                    background-color: #f5f5f5;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding: 20px;
                    background-color: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .qr-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(4, 1fr); 
                    gap: 20px; 
                    margin-bottom: 20px;
                }}
                .qr-item {{ 
                    text-align: center; 
                    page-break-inside: avoid; 
                    padding: 15px; 
                    background-color: white;
                    border: 2px solid #ddd; 
                    border-radius: 10px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .qr-item img {{ 
                    max-width: 150px; 
                    max-height: 150px; 
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }}
                .qr-code {{ 
                    font-size: 10px; 
                    margin-top: 8px; 
                    word-break: break-all; 
                    color: #666;
                    font-family: monospace;
                }}
                .qr-title {{
                    font-size: 12px;
                    font-weight: bold;
                    margin-bottom: 5px;
                    color: #333;
                }}
                @media print {{ 
                    body {{ margin: 10px; background-color: white; }}
                    .qr-grid {{ grid-template-columns: repeat(3, 1fr); gap: 15px; }}
                    .qr-item {{ border: 1px solid #000; }}
                    .header {{ box-shadow: none; }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>IOT Exhibition - Visitor QR Codes</h1>
                <p>Total QR Codes: {len(codes)}</p>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div class="qr-grid">
        """

        for i, code in enumerate(codes, 1):
            html += f"""
                <div class="qr-item">
                    <div class="qr-title">Visitor #{i:03d}</div>
                    <img src="data:image/png;base64,{code['qr_image_base64']}" alt="QR Code">
                    <div class="qr-code">{code['qr_code']}</div>
                </div>
            """

        html += """
            </div>
        </body>
        </html>
        """

        return html


def generate_unique_qr_code() -> str:
    """
    Convenience function to generate a unique QR code

    Returns:
        Unique QR code string
    """
    generator = QRCodeGenerator()
    return generator.generate_unique_qr_code()
