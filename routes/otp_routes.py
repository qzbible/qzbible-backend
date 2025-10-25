# routes/otp_routes.py

from flask import Blueprint, request, jsonify
from marshmallow import ValidationError
from models.user_model import UserModel
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
    Envoyer un code OTP par email
    ---
    tags:
      - OTP
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
              example: "user@example.com"
    responses:
      200:
        description: Code OTP envoyé avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Code OTP envoyé avec succès"
            email:
              type: string
              example: "user@example.com"
      400:
        description: Données invalides
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            errors:
              type: object
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
    """
    try:
        # Valider les données
        data = send_otp_schema.load(request.get_json())
        email = data['email']
        existing_user = UserModel.find_by_email(email)
        if existing_user:
            return jsonify({
                "success": True,
                "message": "Un utilisateur avec cet email existe déjà.",
                'user':existing_user
            }), 409
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
    Vérifier un code OTP
    ---
    tags:
      - OTP
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - code
          properties:
            email:
              type: string
              format: email
              example: "user@example.com"
            code:
              type: string
              example: "123456"
              minLength: 6
              maxLength: 6
    responses:
      200:
        description: Code OTP vérifié avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Code OTP vérifié avec succès"
      401:
        description: Code OTP incorrect ou expiré
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
            attempts_remaining:
              type: integer
      400:
        description: Données invalides
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            errors:
              type: object
      500:
        description: Erreur serveur
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
    Renvoyer un nouveau code OTP
    ---
    tags:
      - OTP
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
              example: "user@example.com"
    responses:
      200:
        description: Nouveau code OTP envoyé avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Nouveau code OTP envoyé avec succès"
      400:
        description: Données invalides
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            errors:
              type: object
      500:
        description: Erreur serveur
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
    Vérifier le statut d'un OTP pour un email donné
    ---
    tags:
      - OTP
    parameters:
      - in: path
        name: email
        type: string
        required: true
        description: Email de l'utilisateur
        example: "user@example.com"
    responses:
      200:
        description: Statut de l'OTP récupéré
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            exists:
              type: boolean
              example: true
            message:
              type: string
            data:
              type: object
              properties:
                email:
                  type: string
                created_at:
                  type: string
                  format: date-time
                expires_at:
                  type: string
                  format: date-time
                time_remaining_seconds:
                  type: integer
                attempts:
                  type: integer
                attempts_remaining:
                  type: integer
                is_verified:
                  type: boolean
      500:
        description: Erreur serveur
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