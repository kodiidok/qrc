import os
import sqlite3
import socket
from datetime import datetime
from flask import Flask, request, jsonify, render_template, abort
from dotenv import load_dotenv  # <-- for loading .env
from config import config
from database import init_db, get_db_stats, reset_db
from utils.qr_generator import QRGenerator

# Load env variables from .env file
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Load config based on environment
env_name = os.getenv('FLASK_ENV')
app.config.from_object(config[env_name])

# Admin token from environment
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN')


def is_authorized():
    """
    Check for valid admin token in Authorization header
    """
    token = request.headers.get('Authorization')
    return token == f"Bearer {ADMIN_TOKEN}"

#
#   DB
#


@app.route('/admin/stats')
def admin_stats():
    if not is_authorized():
        abort(403, description="Unauthorized")
    return jsonify(get_db_stats())


@app.route('/admin/init-db', methods=['POST'])
def admin_init_db():
    if not is_authorized():
        abort(403, description="Unauthorized")
    init_db()
    return jsonify({"message": "Database initialized."})


@app.route('/admin/reset-db', methods=['POST'])
def admin_reset_db():
    if not is_authorized():
        abort(403, description="Unauthorized")
    reset_db()
    return jsonify({"message": "Database reset and reinitialized."})


#
#   QR
#


@app.route('/admin/init-qr-codes', methods=['POST'])
def admin_init_qr_codes():
    if not is_authorized():
        abort(403, description="Unauthorized")
    QRGenerator.init_qr_codes()
    return jsonify({"message": "QR codes initialized."})


@app.route('/admin/reset-qr-codes', methods=['POST'])
def admin_reset_qr_codes():
    if not is_authorized():
        abort(403, description="Unauthorized")
    QRGenerator.reset_qr_codes()
    return jsonify({"message": "QR codes table cleared and reinitialized."})


#
#   APP
#


@app.route('/')
def home():
    return f"App is running with config: {app.config['DB_NAME']}"


if __name__ == '__main__':
    if env_name == 'development':
        print("🔧 Auto-initializing database (dev mode)...")
        init_db()
    app.run(host='127.0.0.1', port=5000, debug=app.config['DEBUG'])
