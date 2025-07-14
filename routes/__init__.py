from flask import Blueprint
from .admin_routes import admin_bp
from .qr_routes import qr_bp
from .app_routes import app_bp


def register_routes(app):
    app.register_blueprint(admin_bp)
    app.register_blueprint(qr_bp)
    app.register_blueprint(app_bp)
