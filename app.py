import os
import sqlite3
import socket
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv  # <-- for loading .env
from config import config

# Load environment variables from a .env file (optional, useful for local/dev)
load_dotenv()

app = Flask(__name__)

# Get environment from OS, default to 'default' if not set
env_name = os.getenv('FLASK_ENV', 'default')
app.config.from_object(config[env_name])


@app.route('/')
def home():
    return f"App is running with config: {app.config['DB_NAME']}"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
