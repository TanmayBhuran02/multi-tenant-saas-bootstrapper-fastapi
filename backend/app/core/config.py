import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
    
    # We will use this mainly for references if needed, but DB URL is in session.py
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        'postgresql+asyncpg://saas:saas@localhost:5432/saas_bootstrapper'
    )
    
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret-change-in-prod')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 86400))  # 24h
    SUPERADMIN_SECRET = os.environ.get('SUPERADMIN_SECRET', 'superadmin-dev-secret')
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
    
    # Fastapi debug mode
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

config = Config()
