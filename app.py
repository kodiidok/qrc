import os
from flask import Flask
from dotenv import load_dotenv
from config import config
from database import init_db
from routes import register_routes

# Load env
load_dotenv()

# Flask app
app = Flask(__name__)
env_name = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env_name])

# Register routes
register_routes(app)

# Auto-init DB for dev
if __name__ == '__main__':
    if env_name == 'development':
        print("🔧 Auto-initializing database...")
        init_db()
    app.run(host='127.0.0.1', port=5000, debug=app.config['DEBUG'])
