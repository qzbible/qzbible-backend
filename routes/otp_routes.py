# routes/otp_routes.py

from flask import Blueprint, request, jsonify
from marshmallow import ValidationError
from schemas.otp_schemas import SendOTPSchema, VerifyOTPSchema, ResendOTPSchema
from models.otp_model import OTPModel
from utils.email import send_otp_mail
 

otp_bp = Blueprint('otp', __name__, url_prefix='/api/otp')

# Initialiser les schémas
send_otp_schema = SendOTPSchema()
verify_otp_schema = VerifyOTPSchema()
resend_otp_schema = ResendOTPSchema()

@otp_bp.route('/send', methods=['POST'])
def send_otp():
    """
    Génère et envoie un OTP par email
    ---
    Body JSON:
    {
        "email": "user@example.com"
    }
    """
    try:
        # Valider les données
        data = send_otp_schema.load(request.get_json())
        email = data['email']
        
        # Créer l'OTP
        otp_code = OTPModel.create_otp(email, expiration_minutes=10)
        
        # Envoyer l'email
        if send_otp_mail(email, otp_code):
            return jsonify({
                "success": True,
                "message": "Code OTP envoyé avec succès",
                "email": email
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Erreur lors de l'envoi de l'email"
            }), 500
            
    except ValidationError as err:
        return jsonify({
            "success": False,
            "errors": err.messages
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur serveur : {str(e)}"
        }), 500

@otp_bp.route('/verify', methods=['POST'])
def verify_otp():
    """
    Vérifie un code OTP
    ---
    Body JSON:
    {
        "email": "user@example.com",
        "code": "123456"
    }
    """
    try:
        # Valider les données
        data = verify_otp_schema.load(request.get_json())
        email = data['email']
        code = data['code']
        
        # Vérifier l'OTP
        result = OTPModel.verify_otp(email, code)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except ValidationError as err:
        return jsonify({
            "success": False,
            "errors": err.messages
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur serveur : {str(e)}"
        }), 500

@otp_bp.route('/resend', methods=['POST'])
def resend_otp():
    """
    Renvoie un nouveau code OTP
    ---
    Body JSON:
    {
        "email": "user@example.com"
    }
    """
    try:
        # Valider les données
        data = resend_otp_schema.load(request.get_json())
        email = data['email']
        
        # Créer un nouveau OTP
        otp_code = OTPModel.create_otp(email, expiration_minutes=10)
        
        # Envoyer l'email
        if send_otp_mail(email, otp_code):
            return jsonify({
                "success": True,
                "message": "Nouveau code OTP envoyé avec succès"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Erreur lors de l'envoi de l'email"
            }), 500
            
    except ValidationError as err:
        return jsonify({
            "success": False,
            "errors": err.messages
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur serveur : {str(e)}"
        }), 500

@otp_bp.route('/status/<email>', methods=['GET'])
def otp_status(email):
    """
    Vérifie le statut d'un OTP pour un email donné
    """
    try:
        otp_info = OTPModel.get_otp_info(email)
        
        if not otp_info:
            return jsonify({
                "success": True,
                "exists": False,
                "message": "Aucun OTP actif pour cet email"
            }), 200
        
        return jsonify({
            "success": True,
            "exists": True,
            "data": otp_info
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur serveur : {str(e)}"
        }), 500