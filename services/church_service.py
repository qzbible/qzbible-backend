# services/church_service.py
from models.church_model import ChurchModel  # Import ChurchModel from the appropriate module
from bson import ObjectId  # Import ObjectId from bson
from werkzeug.utils import secure_filename
from flask import current_app, request
import os  # Import os for file handling
# services/church_service.py

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

# Création d'un nouveau church
"""
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1MzI3OTM2MCwianRpIjoiYTRhZDUzOTktMDhmNS00NDlmLTg5OTUtNDZjYTgwYmY5YzM1IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjY4MTI0ODU0ODI0MGU0NGVlZjE4MzE2NyIsIm5iZiI6MTc1MzI3OTM2MCwiZXhwIjoxNzUzODE5MzYwLCJyb2xlIjoic3RhZmYifQ.Nq8osBLnQvXKbT3iGKCRzZCaMCCLtuglAVnIKwruz0k
"""
def create_church(data, logo_file=None):
    try:
        church_data = {
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

        church_data["logo"] = logo_filename

        
        # Vérifier si l'email du church est déjà utilisé ou des comptes admin
        existing_church = ChurchModel.get_church_by_email(church_data["email"])
        if existing_church:
            return {"message": "Un church avec cet email existe déjà.", "status": 400}
        existing_admin = ChurchModel.get_admin_by_email(admin_data["email"])
        
        if existing_admin:
            return {"message": "Un compte admin avec cet email existe déjà.", "status": 400}
        # Créer le church et l'admin

        result = ChurchModel.create_church(church_data, licence_data, admin_data)
        
        
        return {"message": result["message"], "church_id": result["church_id"], "admin_id": result["admin_id"], "status": 201}

    except KeyError as e:
        return {"message": f"Champ manquant : {str(e)}", "status": 400}
    except Exception as e:
        return {"message": f"Erreur serveur : {str(e)}", "status": 500}


# activer un church ou deasctiver un church
def toggle_church_status_services(church_id):
    """
    Active ou désactive un church en fonction de son ID.
    
    :param church_id: ID du church à activer ou désactiver
    :return: Dictionnaire contenant le message et le statut HTTP
    """
    try:
        result = ChurchModel.toggle_church_status(church_id)
        if result:
            return {"message": "church activé avec succès.", "status": 200}
        else:
            return {"message": "church désactivé avec succès.", "status": 200}
    except Exception as e:
        return {"message": f"Erreur lors de l'activation/désactivation du church : {str(e)}", "status": 500}


#Activer ou désactiver un church  
def toggle_church_status_service(church_id):
    """
    Active ou désactive un church selon son état actuel.

    :param church_id: ID du church à modifier
    :return: Dictionnaire avec message et code HTTP
    """
    try:
        church = ChurchModel.get_church_by_id(church_id)
        if not church:
            return {"message": "church introuvable.", "status": 404}

        new_status = not church.get("is_active", True)

        ChurchModel.collection.update_one(
            {"_id": ObjectId(church_id)},
            {"$set": {"is_active": new_status}}
        )

        return {
            "message": f"church {'activé' if new_status else 'désactivé'} avec succès.",
            "status": 200
        }

    except Exception as e:
        return {
            "message": f"Erreur lors de l'activation/désactivation du church : {str(e)}",
            "status": 500
        }


# Récupérer tous les churchs

def get_all_church_service():
    """
    Récupère tous les churchs.
    
    :return: Liste de dictionnaires contenant les informations de chaque church
    """
    try:
        churchs = ChurchModel.get_all_church()
        # Ajouter les logos si présents
        for church in churchs:
            if church.get("logo"):
                church["logo"] = f"{request.host_url}uploads/images/{church['logo']}" 
        
        return {"church": churchs, "status": 200}
    except Exception as e:
        return {"message": f"Erreur lors de la récupération des church : {str(e)}", "status": 500}
    
    
# Supprimer un church
def delete_church_service(church_id):
    """
    Supprime un church par son ID.
    
    :param church_id: ID du church à supprimer
    :return: Dictionnaire contenant le message et le statut HTTP
    
    """
    church = ChurchModel.get_church_by_id(church_id)
    if not church:
        return {"message": "church non trouvé.", "status": 404}
    
    try:
        result = ChurchModel.delete_church(church_id)
        return {"message": result["message"], "status": 200}
    except Exception as e:
        return {"message": f"Erreur lors de la suppression du church : {str(e)}", "status": 500}


# Mettre à jour un church
def update_church_service(church_id, data, user_role):
    """
    Met à jour les informations d'un church selon le rôle de l'utilisateur.
    - Admin : ne peut pas modifier la licence
    - Staff : peut tout modifier

    :param church_id: ID du church
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
        result = ChurchModel.update_church(church_id, data)
        return {"message": result["message"], "status": 200}
    except Exception as e:
        return {"message": f"Erreur lors de la mise à jour du church : {str(e)}", "status": 500}
    
# Récupère un church par son ID

def get_church_service(church_id):
    """
    Récupère un church par son ID.
    
    :param church_id: ID du church à récupérer
    :return: Dictionnaire contenant les informations du church ou un message d'erreur
    """
    try:
        church = ChurchModel.get_church_by_id(church_id)
        church['logo'] = f"{request.host_url}uploads/images/{church['logo']}" if church.get("logo") else None
        if not church:
            return {"message": "church non trouvé.", "status": 404}
        return {"church": church, "status": 200}
    except Exception as e:
        return {"message": f"Erreur lors de la récupération du church : {str(e)}", "status": 500}
    


def search_churchs_service(search_query=None, pays=None, ville=None, quartier=None):
    """
    Service pour rechercher et filtrer les churchs selon plusieurs critères.
    
    :param search_query: Texte de recherche pour la dénomination (optionnel)
    :param pays: Filtre par pays (optionnel)
    :param ville: Filtre par ville (optionnel)
    :param quartier: Filtre par quartier (optionnel)
    :return: Dictionnaire contenant les churchs filtrés et le statut
    """
    try:
        # Appel de la méthode de recherche du modèle
        churchs = ChurchModel.search_churchs(
            search_query=search_query,
            pays=pays,
            ville=ville,
            quartier=quartier
        )
        
        # Ajouter les URLs complètes des logos si présents
        for church in churchs:
            if church.get("logo"):
                church["logo"] = f"{request.host_url}uploads/images/{church['logo']}"
        
        return  churchs
    
    except Exception as e:
        return {
            "message": f"Erreur lors de la recherche des churchs : {str(e)}",
            "status": 500
        }
    
    
