# services/auth_services.py
from datetime import datetime
from flask import request, jsonify
from models.church_model import ChurchModel
from models.connexion_model import ConnexionModel
from models.user_model import UserModel
from bson import ObjectId
from flask_bcrypt import Bcrypt
from extensions import jwt
from config import Config
 
from flask_jwt_extended import create_access_token, create_refresh_token
from flask import jsonify, current_app
from werkzeug.security import check_password_hash
from extensions import mongo
from datetime import timedelta
from utils.error_handler import handle_error
from utils.email import send_reset_password_email
from utils.jwt_token import generate_validation_token, decode_validation_token



# Initialisation des objets nécessaires
db = mongo.db
bcrypt = Bcrypt()



# Fonction pour activer le compte utilisater
def activate_account(user_id):
    """
    Active le compte utilisateur après validation du token.
    """
    user = UserModel.find_by_id(user_id)
    if not user:
        return handle_error("Utilisateur non trouvé.", 404)
    if user.get("is_active"):
        return handle_error("Le compte est déjà actif.", 400)
    
    UserModel.collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"is_active": True}}
    )

    return jsonify({"message": "Compte Utilisateur activé avec succès."}), 200


# Fonction pour la création d'un utilisateur (manager, livreur)
def create_user_account(store_id, email, password, role):
    """
    Crée un compte utilisateur (manager ou livreur) pour un magasin.
    """
    if UserModel.find_by_email(email):
        return handle_error("Un utilisateur avec cet email existe déjà.", 400)

    user = UserModel(
        username=email,
        email=email,
        password=password,
        role=role,
        store_id=store_id
    )
    user.save()

    return jsonify({"message": f"Compte {role} créé avec succès."}), 201

# Fonction de connexion de l'utilisateur
def login_user(email, password):
    user = db.users.find_one({"email": email})
    if not user:
        return handle_error("Utilisateur non trouvé", 404)
    # retrouver le Church de l'utilisateur
    if user['role'] == "admin" or user["role"] == "manager":
        church = ChurchModel.get_church_by_id(user["church_id"]) if user else None
        if not church:
            return handle_error("Church non trouvé pour cet utilisateur", 404)
        if not church.get("is_active", False):
            return handle_error("Church inactif. Veuillez contacter votre administrateur ou l'équipe de la plateforme", 403)
    if not user:
        return handle_error("Utilisateur non trouvé", 404)
    
    if not user.get("is_active", False):
        return handle_error("Compte inactif. Veuillez vérifier votre email ou contactez votre administrateur", 403)
    
    # Utilisation de bcrypt pour vérifier le mot de passe
    if not bcrypt.check_password_hash(user["password"], password):
        return handle_error("Mot de passe incorrect", 403)

    access_token = create_access_token(
        identity=str(user["_id"]), 
        additional_claims={"role": user["role"]}, 
        expires_delta=timedelta(days=60) 
    )
    refresh_token = create_refresh_token(
        identity=str(user["_id"]), 
        expires_delta=timedelta(days=7)
    )
    
    # Enregistrer la connexion
    ConnexionModel.create_connexion({
        "user_id": user["_id"],
        "email": user["email"],
        "role": user["role"],
        "magasin_id": user.get("magasin_id"),
        "timestamp": datetime.utcnow(),
        "ip_address": request.remote_addr
    })
   
    if user["role"] == "admin" or user["role"] == "manager" or user["role"] == "livreur":
        # Si l'utilisateur est un admin, on lui donne un accès complet
        data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": user["role"],
        "email": user["email"],
        "denomination_church": church["denomination"],
        "church_id": str(church["_id"]),
        "logo_church": f"{request.host_url}uploads/images/{church['logo']}" if church.get("logo") else None,

        }
    else:
        # Si l'utilisateur est un staff, il n'est liée a aucun magasin
        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "role": user["role"],
            "email": user["email"],
        }
    
    return jsonify(data), 200





# Fonction pour rafraîchir le token de l'utilisateur
def refresh_user_token(identity):
    new_token = create_access_token(identity=identity, expires_delta=timedelta(minutes=15))
    return jsonify({"access_token": new_token}), 200





# Service pour reinitialiser le mot de passe
def send_reset_email_service(email):
    """
    Envoie un email de réinitialisation de mot de passe à l'utilisateur
    """
    user = UserModel.find_by_email(email)
    if user:
        token = generate_validation_token(str(user["_id"]))
        send_reset_password_email(user["email"], token)
    return jsonify({"message": "Si cet email existe, un lien a été envoyé"}), 200




# Fonction pour changer le mot de passe
def reset_password_service(token, new_password, confirm_password):
    if new_password != confirm_password:
        return jsonify({"error": "Les mots de passe ne correspondent pas"}), 400

    try:
        user_id = decode_validation_token(token)
        hashed_password = bcrypt.generate_password_hash(new_password)
        success = UserModel.update_password(user_id, hashed_password)
        if success:
            return jsonify({"message": "Mot de passe réinitialisé avec succès"}), 200
        return jsonify({"error": "Utilisateur introuvable"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
    
    
    
# Fonction pour changer le mot de passe de l'utilisateur connecté
def change_user_password_service(user_id, old_password, new_password, confirm_password):
    if new_password != confirm_password:
        return jsonify({"error": "Les mots de passe ne correspondent pas"}), 400

    user = UserModel.find_by_id(user_id)
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    if not bcrypt.check_password_hash(user["password"], old_password):
        return jsonify({"error": "Mot de passe actuel incorrect"}), 401

    hashed_new_password = bcrypt.generate_password_hash(new_password)
    UserModel.update_password(user_id, hashed_new_password)

    return jsonify({"message": "Mot de passe modifié avec succès"}), 200




# services/test_email_service.py

from utils.email import send_validation_email_creation_account

def test_envoi_email_service(email):
    """
    Service de test pour vérifier l'envoi d'email avec adresse dynamique.
    """
    credentials = {
        "name": "Doe",
        "first_name": "John",
        "email": email,
        "role": "manager",
        "password": "123456"  # mot de passe fictif
    }

    print(f"⏳ Tentative d'envoi d'email à {email}")
    try:
        send_validation_email_creation_account(email, credentials)
        return {"message": f"✅ Email envoyé à {email}"}, 200
    except Exception as e:
        return {"error": f"❌ Erreur lors de l'envoi à {email} : {str(e)}"}, 500
