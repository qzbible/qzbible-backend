from utils.jwt_token import decode_validation_token
from flask import Blueprint, request, jsonify
from services.auth_services import (
    activate_account,
    login_user,
    refresh_user_token,
    send_reset_email_service,
    reset_password_service,
    change_user_password_service,
    test_envoi_email_service
    
)
from utils.decorators import staff_required, admin_required, livreur_required
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.email import send_validation_email

auth_bp = Blueprint('auth_bp', __name__)


# Route pour tester l'envoi d'un email
@auth_bp.route("/test-email", methods=["GET"])
def test_email_route():

    email = request.args.get("email")
    if not email:
        return jsonify({"error": "❌ L'adresse email est requise (paramètre ?email=)"}), 400

    result, code = test_envoi_email_service(email)
    return jsonify(result), code




@auth_bp.route('/activate_account/<token>', methods=['POST'])

def activate_user_account(token):
    """
    Activer un compte utilisateur via token
    ---
    tags:
      - Authentification
    parameters:
      - in: path
        name: token
        required: true
        type: string
        description: Jeton de validation
    responses:
      200:
        description: Compte activé
      400:
        description: Erreur de validation
    """
    try:
        user_id = decode_validation_token(token)
        print(user_id)
        return activate_account(user_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Route permettant l'authentification d'un utilisateur

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Connexion d’un utilisateur
    ---
    tags:
      - Authentification
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: "user@example.com"
            password:
              type: string
              example: "password123"
    responses:
      200:
        description: Connexion réussie
      400:
        description: Email ou mot de passe manquant
    """
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email et mot de passe sont requis."}), 400
    
    return login_user(email, password)


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Rafraîchir le token d'accès
    ---
    tags:
      - Authentification
    summary: Rafraîchissement du token JWT
    description: Génère un nouveau token d'accès à partir d'un token de rafraîchissement valide.
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Token de rafraîchissement JWT au format **Bearer &lt;token&gt;**
        default: Bearer 
    responses:
      200:
        description: Nouveau token d'accès généré
        schema:
          type: object
          properties:
            access_token:
              type: string
              example: eyJ0eXAiOiJKV1QiLCJhbGciOi...
      401:
        description: Token invalide ou expiré
    """
    identity = get_jwt_identity()
    return refresh_user_token(identity)






@auth_bp.route('/forgot_password', methods=['POST'])
def forgot_password():
    """
    Envoyer un email de réinitialisation de mot de passe.
    ---
    tags:
      - Authentification
    parameters:
      - in: body
        name: body
        required: true
        description: Email de l'utilisateur
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              example: "utilisateur@example.com"
    responses:
      200:
        description: Email envoyé si l'utilisateur existe
    """
    data = request.get_json()
    email = data.get('email')
    return send_reset_email_service(email)


@auth_bp.route('/reset_password/<token>', methods=['POST'])
def reset_password(token):
    """
    Réinitialiser le mot de passe à l'aide d'un token.
    ---
    tags:
      - Authentification
    parameters:
      - in: path
        name: token
        required: true
        type: string
        description: Token de réinitialisation
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - new_password
            - confirm_password
          properties:
            new_password:
              type: string
              example: "nouveaumotdepasse123"
            confirm_password:
              type: string
              example: "nouveaumotdepasse123"
    responses:
      200:
        description: Mot de passe réinitialisé avec succès
      400:
        description: Token invalide ou mot de passe incorrect
    """
    data = request.get_json()
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")
    return reset_password_service(token, new_password, confirm_password)
  
# modifier son mot de passe
@auth_bp.route('/change_password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Modifier le mot de passe de l'utilisateur connecté.
    ---
    tags:
      - Authentification
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - old_password
            - new_password
            - confirm_password
          properties:
            old_password:
              type: string
              example: "ancienmotdepasse123"
            new_password:
              type: string
              example: "nouveaumotdepasse123"
            confirm_password:
              type: string
              example: "nouveaumotdepasse123"
    responses:
      200:
        description: Mot de passe modifié avec succès
      400:
        description: Erreur dans les données envoyées ou mot de passe incorrect
    """
    data = request.get_json()
    user_id = get_jwt_identity()
    
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    if not old_password or not new_password or not confirm_password:
        return jsonify({"error": "Tous les champs sont requis."}), 400
    
    if new_password != confirm_password:
        return jsonify({"error": "Les nouveaux mots de passe ne correspondent pas."}), 400
    
    # Appel du service pour changer le mot de passe
    return change_user_password_service(user_id, old_password, new_password, confirm_password)


