# config.py
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

def parse_seconds(value, default):
    try:
        if isinstance(value, timedelta):
            return int(value.total_seconds())
        elif isinstance(value, str):
            return int(value)
        elif isinstance(value, int):
            return value
        else:
            return default
    except Exception as e:
        print(f"[⚠️ CONFIG] Erreur de conversion JWT_EXPIRES : {e}")
        return default

class Config:
    """Configuration principale de l'application."""
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    # Expiration des tokens
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=parse_seconds(os.getenv("JWT_ACCESS_TOKEN_EXPIRES"), 900))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=parse_seconds(os.getenv("JWT_REFRESH_TOKEN_EXPIRES"), 2592000))
    JWT_TOKEN_LOCATION = ['headers']
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI")
    print(f"[DEBUG] MONGO_URI = {MONGO_URI}")

    # SMTP - pour l'envoi de mail
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
    MAIL_SENDER = os.getenv("MAIL_SENDER")

    # CORS
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

    # Dossier pour les images uploadées
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads", "images")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 Mo max
    # Durée de vie du token de validation par email (ex: 1 jour)
    VALIDATION_TOKEN_EXPIRES = 86400  # secondes = 24 heures
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads", "images")
    STAFF_IMAGE_FOLDER = os.path.join(os.getcwd(), "uploads", "staff_images")
