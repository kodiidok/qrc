"""
Configuration settings for the IOT Exhibition application
"""

import os
from dotenv import load_dotenv  # <-- for loading .env
load_dotenv()


class Config:
    """Base configuration class"""

    # Database settings (default; can be overridden per environment)
    DB_NAME = os.getenv('DB_NAME', 'iot2025.db')

    # Minimum visits required for sticker eligibility
    MIN_VISITS_FOR_STICKER = int(os.getenv('MIN_VISITS_FOR_STICKER'))

    # QR Code generation settings
    MAX_QR_CODES_PER_BATCH = int(os.getenv('MAX_QR_CODES_PER_BATCH'))
    DEFAULT_QR_CODE_COUNT = int(os.getenv('DEFAULT_QR_CODE_COUNT'))

    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    # QR Code image settings
    QR_CODE_VERSION = int(os.getenv('QR_CODE_VERSION', 1))
    QR_CODE_BOX_SIZE = int(os.getenv('QR_CODE_BOX_SIZE', 10))
    QR_CODE_BORDER = int(os.getenv('QR_CODE_BORDER', 4))
    QR_CODE_FILL_COLOR = os.getenv('QR_CODE_FILL_COLOR', 'black')
    QR_CODE_BACK_COLOR = os.getenv('QR_CODE_BACK_COLOR', 'white')

    # Pagination settings
    DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', 50))
    MAX_PAGE_SIZE = int(os.getenv('MAX_PAGE_SIZE', 100))


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    DB_NAME = os.getenv('DB_NAME')


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY')


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DB_NAME = ':memory:'  # Use in-memory database for testing


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
