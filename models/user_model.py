# models/user_model.py

from datetime import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash
from flask_bcrypt import Bcrypt
from app import mongo


bcrypt = Bcrypt()
class UserModel:
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.users
    
    collection = mongo.db.users

    @staticmethod
    def create_staff(name, first_name, email, password):
        user = {
            "name" : name,
            "first_name": first_name,
            "email": email.lower(),
            "role": "staff",
            "password": password,
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        result = UserModel.get_collection().insert_one(user)
        return str(result.inserted_id)
    
    @staticmethod
    def create_admin(name, first_name, email, password, church_id, role="admin"):
        user = {
            "name" : name,
            "first_name": first_name,
            "email": email.lower(), 
            "church_id": ObjectId(church_id),
            "role": role,
            "password": bcrypt.generate_password_hash(password),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = UserModel.get_collection().insert_one(user)
        return str(result.inserted_id)
    
    
    @staticmethod
    def create_manager(name, first_name, email, password, church_id):
        user = {
            "name" : name,
            "first_name": first_name,
            "email": email.lower(),
            "role": "manager",
            "password": bcrypt.generate_password_hash(password),
            "church_id": ObjectId(church_id),
            "is_active": True,
            "created_at": datetime.utcnow()
            }
        result = UserModel.get_collection().insert_one(user)
        return str(result.inserted_id)
    
    
    
    @staticmethod
    def create_simple_user(name, age_group, email, password, church_id):
        user = {
            "name" : name,
            "age_group": age_group,
            "email": email.lower(),
            "role": "simple_user",
            "password": bcrypt.generate_password_hash(password),
            "church_id": ObjectId(church_id),
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        result = UserModel.get_collection().insert_one(user)
        return str(result.inserted_id)

    @staticmethod
    def activate_user(user_id, password):
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        result = UserModel.get_collection().update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password": hashed_password,
                    "is_active": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
  
    @staticmethod
    def find_by_email(email):
        return UserModel.get_collection().find_one({"email": email.lower()})

    
    @staticmethod
    def find_by_id(user_id):
        return UserModel.get_collection().find_one({"_id": ObjectId(user_id)})



    
    @staticmethod
    def count_users_by_role(church_id, role):
        """
        Compte le nombre d'utilisateurs par rôle dans un magasin donné.
        :param church_id: ID du church
        :param role: Rôle de l'utilisateur (manager, livreur)
        :return: Nombre d'utilisateurs avec le rôle spécifié
        """
        if role not in ["manager"]:
            raise ValueError("Rôle inconnu. Utilisez 'manager' ou 'livreur'.")
        if not ObjectId.is_valid(church_id):
            raise ValueError("ID de church invalide.")
        return UserModel.get_collection().count_documents({"church_id": ObjectId(church_id), "role": role})
    
    #Mettre à jour le champs avatar ou ajouter un avatar
    @staticmethod
    def update_avatar(user_id, avatar_url):
        result = UserModel.get_collection().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"avatar": avatar_url}}
        )
        return result.modified_count > 0
   
    # Récupérer les informations d'un utilisateur
    @staticmethod
    def get_user_by_id(user_id):
        user = UserModel.get_collection().find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
            user.pop("password", None)  # On ne renvoie jamais le mot de passe
        return user
    

    
    @staticmethod
    def update_password(user_id, hashed_password):
        """
        Met à jour le mot de passe d'un utilisateur.
        :param user_id: ID de l'utilisateur
        :param hashed_password: Nouveau mot de passe haché
        :return: True si la mise à jour a réussi, False sinon
        """
        if not ObjectId.is_valid(user_id):
            raise ValueError("ID d'utilisateur invalide.")
        result = UserModel.get_collection().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password": hashed_password}}
        )
        return result.modified_count > 0
   
    
    @staticmethod
    def delete_user(user_id):
        """
        Supprime un utilisateur par son ID.
        :param user_id: ID de l'utilisateur à supprimer
        :return: Dictionnaire contenant le message et le statut HTTP
        """
        if not ObjectId.is_valid(user_id):
            return {"message": "ID d'utilisateur invalide.", "status": 400}
        
        result = UserModel.get_collection().delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            return {"message": "Utilisateur non trouvé.", "status": 404}
        
        return {"message": "Utilisateur supprimé avec succès.", "status": 200}
    
    @staticmethod
    def update_user(user_id, data):
        """
        Met à jour les informations d'un utilisateur.
        :param user_id: ID de l'utilisateur à mettre à jour
        :param data: Dictionnaire contenant les nouvelles données de l'utilisateur
        :return: Dictionnaire contenant le message et le statut HTTP
        """
        if not ObjectId.is_valid(user_id):
            return {"message": "ID d'utilisateur invalide.", "status": 400}
        
        result = UserModel.get_collection().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": data}
        )
        
        if result.modified_count == 0:
            return {"message": "Aucune modification effectuée ou utilisateur non trouvé.", "status": 404}
        
        return {"message": "Utilisateur mis à jour avec succès.", "status": 200}
    @staticmethod
    def get_all_users():
        """
        Récupère tous les utilisateurs.
        :return: Liste de dictionnaires contenant les informations de chaque utilisateur
        """
        return list(UserModel.get_collection().find())


    @staticmethod
    def reset_password(user_id, new_password="123456"):
        hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")
        
        result = UserModel.get_collection().update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password": hashed_password,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
