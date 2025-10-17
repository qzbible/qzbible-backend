# services/magasin_service.py
from models.magasin_model import MagasinModel  # Import MagasinModel from the appropriate module
from bson import ObjectId  # Import ObjectId from bson
from werkzeug.utils import secure_filename
from flask import current_app, request
import os  # Import os for file handling
# services/magasin_service.py

from marshmallow.exceptions import ValidationError

def validate_licence(licence):
    if "type" not in licence or "max_managers" not in licence or "max_livreurs" not in licence:
        raise ValidationError("Le champ licence doit contenir 'type', 'max_managers' et 'max_livreurs'.")
    
    # Assurance que les valeurs sont valides
    if not isinstance(licence["type"], str):
        raise ValidationError("Le type de licence doit être une chaîne de caractères.")
    
    if not isinstance(licence["max_managers"], int) or licence["max_managers"] < 1:
        raise ValidationError("Le nombre maximal de managers doit être un entier positif.")
    
    if not isinstance(licence["max_livreurs"], int) or licence["max_livreurs"] < 1:
        raise ValidationError("Le nombre maximal de livreurs doit être un entier positif.")

# Création d'un nouveau magasin
"""
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1MzI3OTM2MCwianRpIjoiYTRhZDUzOTktMDhmNS00NDlmLTg5OTUtNDZjYTgwYmY5YzM1IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjY4MTI0ODU0ODI0MGU0NGVlZjE4MzE2NyIsIm5iZiI6MTc1MzI3OTM2MCwiZXhwIjoxNzUzODE5MzYwLCJyb2xlIjoic3RhZmYifQ.Nq8osBLnQvXKbT3iGKCRzZCaMCCLtuglAVnIKwruz0k
"""
def create_magasin(data, logo_file=None):
    try:
        magasin_data = {
            "denomination": data["denomination"],
            "pays": data["pays"],
            "ville": data["ville"],
            "quartier": data["quartier"],
            "email": data["email"],
            "activité": data["activité"]
        }

        licence_data = {
            "nombre_manager": data["nombre_manager"],
            "nombre_livreur": data["nombre_livreur"]
        }

        admin_data = {
            "name": data["admin"]["name"],
            "first_name": data["admin"]["first_name"],
            "email": data["admin"]["email"],
            "password": data["admin"]["password"]
        }
        
        # Gestion du logo
        logo_filename = None
        if logo_file:
            filename = secure_filename(logo_file.filename)
            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            logo_path = os.path.join(upload_dir, filename)
            logo_file.save(logo_path)
            logo_filename = filename

        magasin_data["logo"] = logo_filename

        
        # Vérifier si l'email du magasin est déjà utilisé ou des comptes admin
        existing_magasin = MagasinModel.get_magasin_by_email(magasin_data["email"])
        if existing_magasin:
            return {"message": "Un magasin avec cet email existe déjà.", "status": 400}
        existing_admin = MagasinModel.get_admin_by_email(admin_data["email"])
        
        if existing_admin:
            return {"message": "Un compte admin avec cet email existe déjà.", "status": 400}
        # Créer le magasin et l'admin

        result = MagasinModel.create_magasin(magasin_data, licence_data, admin_data)
        
        
        return {"message": result["message"], "magasin_id": result["magasin_id"], "admin_id": result["admin_id"], "status": 201}

    except KeyError as e:
        return {"message": f"Champ manquant : {str(e)}", "status": 400}
    except Exception as e:
        return {"message": f"Erreur serveur : {str(e)}", "status": 500}


# activer un magasin ou deasctiver un magasin
def toggle_magasin_status_services(magasin_id):
    """
    Active ou désactive un magasin en fonction de son ID.
    
    :param magasin_id: ID du magasin à activer ou désactiver
    :return: Dictionnaire contenant le message et le statut HTTP
    """
    try:
        result = MagasinModel.toggle_magasin_status(magasin_id)
        if result:
            return {"message": "Magasin activé avec succès.", "status": 200}
        else:
            return {"message": "Magasin désactivé avec succès.", "status": 200}
    except Exception as e:
        return {"message": f"Erreur lors de l'activation/désactivation du magasin : {str(e)}", "status": 500}


#Activer ou désactiver un magasin  
def toggle_magasin_status_service(magasin_id):
    """
    Active ou désactive un magasin selon son état actuel.

    :param magasin_id: ID du magasin à modifier
    :return: Dictionnaire avec message et code HTTP
    """
    try:
        magasin = MagasinModel.get_magasin_by_id(magasin_id)
        if not magasin:
            return {"message": "Magasin introuvable.", "status": 404}

        new_status = not magasin.get("is_active", True)

        MagasinModel.collection.update_one(
            {"_id": ObjectId(magasin_id)},
            {"$set": {"is_active": new_status}}
        )

        return {
            "message": f"Magasin {'activé' if new_status else 'désactivé'} avec succès.",
            "status": 200
        }

    except Exception as e:
        return {
            "message": f"Erreur lors de l'activation/désactivation du magasin : {str(e)}",
            "status": 500
        }


# Récupérer tous les magasins

def get_all_magasin_service():
    """
    Récupère tous les magasins.
    
    :return: Liste de dictionnaires contenant les informations de chaque magasin
    """
    try:
        magasins = MagasinModel.get_all_magasin()
        # Ajouter les logos si présents
        for magasin in magasins:
            if magasin.get("logo"):
                magasin["logo"] = f"{request.host_url}uploads/images/{magasin['logo']}" 
        
        return {"church": magasins, "status": 200}
    except Exception as e:
        return {"message": f"Erreur lors de la récupération des church : {str(e)}", "status": 500}
    
    
# Supprimer un magasin
def delete_magasin_service(magasin_id):
    """
    Supprime un magasin par son ID.
    
    :param magasin_id: ID du magasin à supprimer
    :return: Dictionnaire contenant le message et le statut HTTP
    
    """
    magasin = MagasinModel.get_magasin_by_id(magasin_id)
    if not magasin:
        return {"message": "Magasin non trouvé.", "status": 404}
    
    try:
        result = MagasinModel.delete_magasin(magasin_id)
        return {"message": result["message"], "status": 200}
    except Exception as e:
        return {"message": f"Erreur lors de la suppression du magasin : {str(e)}", "status": 500}


# Mettre à jour un magasin
def update_magasin_service(magasin_id, data, user_role):
    """
    Met à jour les informations d'un magasin selon le rôle de l'utilisateur.
    - Admin : ne peut pas modifier la licence
    - Staff : peut tout modifier

    :param magasin_id: ID du magasin
    :param update_data: données à mettre à jour
    :param user_role: rôle de l'utilisateur (admin ou staff)
    :return: message de succès ou d'erreur
    """
    # Si l'utilisateur n'est pas staff, on supprime la licence des updates
    licensee = data.get("licence")
    if user_role == "admin":
        if licensee:
            del data["licence"]
  
    try:
        result = MagasinModel.update_magasin(magasin_id, data)
        return {"message": result["message"], "status": 200}
    except Exception as e:
        return {"message": f"Erreur lors de la mise à jour du magasin : {str(e)}", "status": 500}
    
# Récupère un magasin par son ID

def get_magasin_service(magasin_id):
    """
    Récupère un magasin par son ID.
    
    :param magasin_id: ID du magasin à récupérer
    :return: Dictionnaire contenant les informations du magasin ou un message d'erreur
    """
    try:
        magasin = MagasinModel.get_magasin_by_id(magasin_id)
        magasin['logo'] = f"{request.host_url}uploads/images/{magasin['logo']}" if magasin.get("logo") else None
        if not magasin:
            return {"message": "Magasin non trouvé.", "status": 404}
        return {"magasin": magasin, "status": 200}
    except Exception as e:
        return {"message": f"Erreur lors de la récupération du magasin : {str(e)}", "status": 500}
    
    
