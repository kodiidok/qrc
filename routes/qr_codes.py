from flask import Blueprint, request, jsonify
import sqlite3
import qrcode
import io
import base64
from datetime import datetime
import random
import string

qr_codes_bp = Blueprint('qr_codes', __name__)

DB_NAME = 'exhibition-database.db'

# Generate unique QR code string


def generate_qr_code():
    """Generate a unique QR code string"""
    timestamp = str(int(datetime.now().timestamp()))
    random_string = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=8))
    return f"VISITOR_{timestamp}_{random_string}"


@qr_codes_bp.route('/admin/generate-qr-codes', methods=['POST'])
def generate_qr_codes():
    """
    Generate 500 unique QR codes and store them in the database
    """
    try:
        data = request.get_json() if request.is_json else {}
        count = data.get('count', 500)

        if count > 1000:
            return jsonify({'error': 'Maximum 1000 QR codes can be generated at once'}), 400

        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()

            generated_codes = []
            existing_codes = set()

            # Get existing QR codes to avoid duplicates
            cur.execute("SELECT qr_code FROM qr_codes")
            existing_codes = {row[0] for row in cur.fetchall()}

            # Generate unique QR codes
            attempts = 0
            while len(generated_codes) < count and attempts < count * 3:
                qr_code_text = generate_qr_code()
                attempts += 1

                if qr_code_text not in existing_codes:
                    # Generate QR code image
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(qr_code_text)
                    qr.make(fit=True)

                    # Create QR code image
                    qr_image = qr.make_image(
                        fill_color="black", back_color="white")

                    # Convert to base64 for storage
                    img_buffer = io.BytesIO()
                    qr_image.save(img_buffer, format='PNG')
                    img_base64 = base64.b64encode(
                        img_buffer.getvalue()).decode()

                    generated_codes.append({
                        'qr_code': qr_code_text,
                        'qr_image': img_base64
                    })
                    existing_codes.add(qr_code_text)

            if len(generated_codes) < count:
                return jsonify({
                    'error': f'Could only generate {len(generated_codes)} unique codes out of {count} requested'
                }), 400

            # Insert QR codes into database
            for code_data in generated_codes:
                cur.execute("""
                    INSERT INTO qr_codes (qr_code, qr_image_base64) 
                    VALUES (?, ?)
                """, (code_data['qr_code'], code_data['qr_image']))

                # Also insert into visitors table for tracking
                cur.execute("""
                    INSERT INTO visitors (visitor_qr, qr_code_image) 
                    VALUES (?, ?)
                """, (code_data['qr_code'], code_data['qr_image']))

            conn.commit()

            return jsonify({
                'message': f'Successfully generated {len(generated_codes)} QR codes',
                'generated_count': len(generated_codes),
                # Show first 10 as sample
                'codes': [code['qr_code'] for code in generated_codes[:10]]
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@qr_codes_bp.route('/admin/qr-codes', methods=['GET'])
def get_qr_codes():
    """
    Get list of all generated QR codes with their status
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page

        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Get total count
            cur.execute("SELECT COUNT(*) as total FROM qr_codes")
            total_codes = cur.fetchone()['total']

            # Get paginated results
            cur.execute("""
                SELECT qc.*, v.total_visits, v.sticker_dispensed, v.first_visit, v.last_visit
                FROM qr_codes qc
                LEFT JOIN visitors v ON qc.qr_code = v.visitor_qr
                ORDER BY qc.generated_time DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))

            codes = cur.fetchall()

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

            return jsonify({
                'total_codes': total_codes,
                'page': page,
                'per_page': per_page,
                'total_pages': (total_codes + per_page - 1) // per_page,
                'codes': code_list
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@qr_codes_bp.route('/admin/qr-codes/<qr_code>/image', methods=['GET'])
def get_qr_image(qr_code):
    """
    Get QR code image for a specific code
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute(
                "SELECT qr_image_base64 FROM qr_codes WHERE qr_code = ?", (qr_code,))
            result = cur.fetchone()

            if not result:
                return jsonify({'error': 'QR code not found'}), 404

            return jsonify({
                'qr_code': qr_code,
                'image_base64': result['qr_image_base64']
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@qr_codes_bp.route('/admin/qr-codes/print-batch', methods=['POST'])
def mark_codes_printed():
    """
    Mark QR codes as printed
    """
    try:
        data = request.get_json()
        qr_codes = data.get('qr_codes', [])

        if not qr_codes:
            return jsonify({'error': 'No QR codes provided'}), 400

        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()

            # Update printed status
            placeholders = ','.join(['?' for _ in qr_codes])
            cur.execute(f"""
                UPDATE qr_codes 
                SET is_printed = TRUE 
                WHERE qr_code IN ({placeholders})
            """, qr_codes)

            updated_count = cur.rowcount
            conn.commit()

            return jsonify({
                'message': f'Marked {updated_count} QR codes as printed',
                'updated_count': updated_count
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@qr_codes_bp.route('/admin/qr-codes/distribute-batch', methods=['POST'])
def mark_codes_distributed():
    """
    Mark QR codes as distributed to visitors
    """
    try:
        data = request.get_json()
        qr_codes = data.get('qr_codes', [])

        if not qr_codes:
            return jsonify({'error': 'No QR codes provided'}), 400

        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()

            # Update distributed status
            placeholders = ','.join(['?' for _ in qr_codes])
            cur.execute(f"""
                UPDATE qr_codes 
                SET is_distributed = TRUE 
                WHERE qr_code IN ({placeholders})
            """, qr_codes)

            updated_count = cur.rowcount
            conn.commit()

            return jsonify({
                'message': f'Marked {updated_count} QR codes as distributed',
                'updated_count': updated_count
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@qr_codes_bp.route('/admin/qr-codes/export', methods=['GET'])
def export_qr_codes():
    """
    Export QR codes for printing - returns HTML page with all QR codes
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT qr_code, qr_image_base64 
                FROM qr_codes 
                ORDER BY generated_time
            """)

            codes = cur.fetchall()

            # Generate HTML page with QR codes for printing
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>QR Codes for Printing</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .qr-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
                    .qr-item { text-align: center; page-break-inside: avoid; padding: 10px; border: 1px solid #ccc; }
                    .qr-item img { max-width: 150px; max-height: 150px; }
                    .qr-code { font-size: 10px; margin-top: 5px; word-break: break-all; }
                    @media print { .qr-grid { grid-template-columns: repeat(3, 1fr); } }
                </style>
            </head>
            <body>
                <h1>IOT Exhibition - Visitor QR Codes</h1>
                <p>Total QR Codes: {}</p>
                <div class="qr-grid">
            """.format(len(codes))

            for code in codes:
                html += f"""
                    <div class="qr-item">
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

    except Exception as e:
        return str(e), 500
