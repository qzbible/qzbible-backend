 
from models.user_model import UserModel
 
from datetime import datetime
from flask_bcrypt import Bcrypt
from models.church_model import ChurchModel
from services.auth_services import login_user_simple
from utils.email import send_validation_email, send_validation_email_creation_account
from utils.jwt_token import generate_validation_token
from flask import jsonify, current_app
from utils.error_handler import handle_error
from bson import ObjectId

from flask_jwt_extended import get_jwt_identity
 
bcrypt = Bcrypt()



# Fonction pour la création d'un compte staff
def create_staff_account(name, first_name, email, password, confirm_password):
    """
    Crée un compte staff avec un mot de passe haché. L'utilisateur sera inactif par défaut.
    """
    existing_user = UserModel.find_by_email(email)
    if existing_user:
        return handle_error("Un compte avec cet email existe déjà.", 400)

    if password != confirm_password:
        return handle_error("Les mots de passe ne correspondent pas.", 400)
    # Hachage du mot de passe
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
    user_id = UserModel.create_staff(name=name, first_name=first_name, email=email, password=hashed_password)
    
    return jsonify({"message": "Compte staff créé avec succès.", 
                    "user_id": str(user_id),
                    "email": email,
                    "name": name,
                    "first_name": first_name,
                    "role": "staff",
                    "is_active": True
                    }), 201

# Fonction pour la création d'un compte admin
def create_admin_account(name, first_name, email, password, church_id):
    """
    Crée un compte admin désactivé, génère un token de validation, 
    et envoie un lien de validation par email.
    """
    existing_user = UserModel.find_by_email(email)
    if existing_user:
        return handle_error("Un compte avec cet email existe déjà.", 400)

    user_id = UserModel.create_admin(name=name, first_name=first_name, email=email,password=password,  church_id=church_id)
    #token = generate_validation_token(user_id)
    credentials = {
        "name": name,
        "first_name": first_name,
        "email": email,
        "role": "admin",

    }
    #send_validation_email(email, token)
    send_validation_email_creation_account(email, credentials)
    return jsonify({"message": "Compte admin créé. Un email de validation a été envoyé."}), 201


# Activer un compte utilisateur par email
def activate_user_by_email(email, password):
    try:
        user = UserModel.find_by_email(email)
        if not user:
            return {"message": "Utilisateur introuvable", "status": 404}

        if user.get("is_active", False):
            return {"message": "Le compte est déjà activé", "status": 200}


        # Hachage du mot de passe
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        
        UserModel.collection.update_one(
            {"email": email.lower()},
            {
                "$set": {
                    "is_active": True,
                    "password": hashed_password,
                }
            }
        )
    
        return {"message": "Compte activé avec succès"}

    except Exception as e:
        return {"message": f"Erreur lors de l’activation : {str(e)}", "status": 500}


# Activer un compte utilisateur par id
def activate_user_by_id(user_id):
    try:
        user = UserModel.find_by_id(user_id)
        if not user:
            return {"message": "Utilisateur introuvable", "status": 404}

        if user.get("is_active", True):
            return {"message": "Le compte est déjà activé", "status": 200}

        UserModel.collection.update_one(
            {"id": user_id},  
            {
                "$set": {
                    "is_active": True
                }
            }
        )
    
        return {"message": "Compte activé avec succès", "status": 200}

    except Exception as e:
        return {"message": f"Erreur lors de l’activation : {str(e)}", "status": 500}


# Fonction pour désactiver un compte utilisateur par id
def deactivate_user_by_id(user_id):
    try:
        user = UserModel.find_by_id(user_id)
        #print("ID de l'utilisateur :", user_id)
        if not user:
            return {"message": "Utilisateur introuvable", "status": 404}

        if user.get("is_active", False):
            return {"message": "Le compte est déjà désactivé", "status": 200}

        UserModel.collection.update_one(
            {"id": user_id},  # CORRIGÉ ICI
            {
                "$set": {
                    "is_active": False
                }
            }
        )
    
        return {"message": "Compte activé avec succès", "status": 200}

    except Exception as e:
        return {"message": f"Erreur lors de l’activation : {str(e)}", "status": 500}
    


# Fonction pour activer ou désactiver un compte utilisateur

def set_user_activation(user_id, activate=True):
    try:
        if not ObjectId.is_valid(user_id):
            return {"message": "ID utilisateur invalide", "status": 400}

        user = UserModel.find_by_id(user_id)
        if not user:
            return {"message": "Utilisateur introuvable", "status": 404}

        current_status = user.get("is_active", False)

        if current_status == activate:
            status_text = "activé" if activate else "désactivé"
            return {"message": f"Le compte est déjà {status_text}", "status": 200}

        UserModel.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": activate}}
        )

        status_text = "activé" if activate else "désactivé"
        return {"message": f"Compte {status_text} avec succès", "status": 200}

    except Exception as e:
        return {"message": f"Erreur lors de la modification : {str(e)}", "status": 500}


# Vérifie si la limite de rôles pour un magasin est atteinte
def check_role_limit(store_id, role):
    """
    Vérifie si la limite de rôles pour un magasin est atteinte.
    :param store_id: L'ID du magasin.
    :param role: Le rôle de l'utilisateur (manager ou livreur).
    :return: True si la limite n'est pas atteinte, False si elle est atteinte.
    """
    # Récupérer les informations du magasin
    magasin = ChurchModel.get_church_by_id(store_id)
    if not magasin:
        raise ValueError("Magasin non trouvé.")
    
    # Vérifier la limite des managers ou livreurs en fonction du rôle
    if role == "manager":
        current_managers_count = UserModel.count_users_by_role(store_id, "manager")
        if current_managers_count >= magasin["licence"]["max_managers"]:
            return False  # Limite atteinte pour les managers
    
    
    return True  # La limite n'est pas atteinte

 

# Créer un compte livreur
def create_simple_user(name, age_group, email, password, church_id):
    """
    Crée un compte simple avec les informations fournies.
    
    :param name: Nom du user
    :param age_group: Groupe d'âge du user
    :param email: Email du suer
    :param password: Mot de passe du user
    :return: Dictionnaire contenant le message et l'ID du livreur créé
    """
    
    """
    verifie si la limite n'est pas atteinte.
    """
   
    try:
        existing_user = UserModel.find_by_email(email)
        if existing_user:
            return {"message": "Un compte avec cet email existe déjà.", "status": 409}

        user_id = UserModel.create_simple_user(name=name, age_group=age_group, email=email, password=password, church_id=church_id)
         
        credentials = {
            "name": name,
            "first_name": age_group,
            "email": email,
            "role": "simple_user",
            "password": password
        }
        send_validation_email_creation_account(email, credentials)

        return {"message": "Compte livreur créé avec succès.", "user_id": str(user_id), "status": 201, "access": login_user_simple(email)}
    
    except Exception as e:
        return {"message": f"Erreur lors de la création du compte livreur : {str(e)}", "status": 500}
  
  
  
# créer un compte manager  
def create_manager(name, first_name, email,password, church_id):
    """
    Crée un compte manager avec les informations fournies.
    
    :param name: Nom du manager
    :param first_name: Prénom du manager
    :param email: Email du manager
    :param password: Mot de passe du manager
    :return: Dictionnaire contenant le message et l'ID du manager créé
    """
    
    """
    Verification de la non atteinte de la limite de creation des manager conformément à la licence
    """
    if not check_role_limit(church_id, "manager"):
        return {"error": "Limite de managers atteinte pour ce magasin."}, 400
    try:
        existing_user = UserModel.find_by_email(email)
        if existing_user:
            return {"message": "Un compte avec cet email existe déjà.", "status": 400}

        user_id = UserModel.create_manager(name=name, first_name=first_name, email=email, password=password, church_id=church_id)
        
        token = generate_validation_token(user_id)
        #send_validation_email(email, token)
        crendentials = {
            "name": name,
            "first_name": first_name,
            "email": email,
            "role": "manager",
            "password": password
        }
        send_validation_email_creation_account(email, crendentials)

        return {"message": "Compte manager créé avec succès.", "user_id": str(user_id), "status": 201}
    
    except Exception as e:
        return {"message": f"Erreur lors de la création du compte manager : {str(e)}", "status": 500}
    
   

# Fonction pour supprimer un utilisateur par son ID
def delete_user_service(user_id):
    """
    Supprime un utilisateur par son ID.

    - Si l'utilisateur est un livreur :
        - Vérifie s’il a des livraisons non terminées → refuse suppression
        - Réintègre son stock dans le stock magasin
        - Supprime son stock
    - Supprime ensuite l'utilisateur

    :param user_id: ID de l'utilisateur à supprimer
    :return: Dictionnaire contenant le message et le statut HTTP
    """
    try:
        user = UserModel.get_user_by_id(user_id)
        if not user:
            return {"message": "Utilisateur non trouvé.", "status": 404}


        # Suppression de l'utilisateur
        result = UserModel.delete_user(user_id)
        if result["status"] == 200:
            return {"message": result["message"], "status": 200}
        else:
            return {"message": result["message"], "status": result["status"]}

    except Exception as e:
        return {"message": f"Erreur lors de la suppression de l'utilisateur : {str(e)}", "status": 500}
   
    
# Mettre à jour les informations d'un utilisateur
   
def update_user_service(user_id, data):
    """
    Met à jour les informations d'un utilisateur.
    
    :param user_id: ID de l'utilisateur à mettre à jour
    :param data: Dictionnaire contenant les nouvelles données de l'utilisateur
    :return: Dictionnaire contenant le message et le statut HTTP
    """
    try:
        result = UserModel.update_user(user_id, data)
        if result["status"] == 200:
            return {"message": "Utilisateur mis à jour avec succès.", "status": 200}
        else:
            return {"message": result["message"], "status": result["status"]}
    
    except Exception as e:
        return {"message": f"Erreur lors de la mise à jour de l'utilisateur : {str(e)}", "status": 500}
    


def get_all_users_service():
    """
    Récupère tous les utilisateurs :
    - Si l'utilisateur connecté est 'staff' => retourne tous les utilisateurs.
    - Sinon => retourne uniquement les utilisateurs de son magasin.
    """
    try:
        current_user_id = get_jwt_identity()
        user = UserModel.find_by_id(current_user_id)

        if not user:
            return {"message": "Utilisateur connecté introuvable", "status": 404}

        # Récupération des utilisateurs selon le rôle
        if user["role"] == "staff":
            users = UserModel.get_all_users()
        else:
            church_id = user.get("church_id")
            if not church_id:
                return {"message": "Church introuvable pour cet utilisateur", "status": 400}

            users = list(UserModel.collection.find({"church_id": church_id}))
            

        # Conversion des ObjectId et uniformisation des clés
        for u in users:
            # Assurer que "_id" est une string
            if "_id" in u:
                u["_id"] = str(u["_id"])
            # Supprimer l’éventuel champ "id"
            if "id" in u:
                del u["id"]
            # Supprimer le champ "password" pour des raisons de sécurité
            if "password" in u:
                del u["password"]
            # Convertir magasin_id en string si c’est un ObjectId
            if "church_id" in u and isinstance(u["church_id"], ObjectId):
                u["church_id"] = str(u["church_id"])
            if user["role"] == "manager":
                users = [u for u in users if u.get("role") != "admin"]

        # Supprimer le staff de la liste des utilisateurs
        users = [u for u in users if u.get("role") != "staff"]
        # Trier les utilisateurs par date de création
        users.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)

        return {"users": users, "status": 200}

    except Exception as e:
        return {"message": f"Erreur lors de la récupération des utilisateurs : {str(e)}", "status": 500}


def get_user_by_id_service(user_id):
    """
    Récupère un utilisateur par son ID.
    
    :param user_id: ID de l'utilisateur à récupérer
    :return: Dictionnaire contenant les informations de l'utilisateur ou un message d'erreur
    """
    try:
        user = UserModel.get_user_by_id(user_id)
        if not user:
            return {"message": "Utilisateur non trouvé.", "status": 404}
        
        return {"user": user, "status": 200}
    
    except Exception as e:
        return {"message": f"Erreur lors de la récupération de l'utilisateur : {str(e)}", "status": 500}


# Service permettant de reinitialiser le mot de passe d'un utilisateur par l'admin ou le manager
def reset_password_service(user_id, data):
    new_password = data.get("new_password", "123456")  # mot de passe par défaut
    success = UserModel.reset_password(user_id, new_password)
    
    if not success:
        return {"error": "Utilisateur non trouvé ou non mis à jour"}, 404

    return {
        "message": "Mot de passe réinitialisé avec succès",
        "nouveau_mot_de_passe": new_password
    }, 200