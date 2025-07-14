# Routes package initialization file
# This file makes the routes directory a Python package

from .admin import admin_bp
from .team import team_bp
from .visitor import visitor_bp
from .qr_codes import qr_codes_bp

__all__ = ['admin_bp', 'team_bp', 'visitor_bp', 'qr_codes_bp']
