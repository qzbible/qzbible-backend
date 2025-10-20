from datetime import datetime
from bson import ObjectId
from extensions import mongo
from models.user_model import UserModel
from utils.jwt_token import generate_validation_token
from utils.email import send_validation_email, send_validation_email_creation_account
from models.approvisionnement_model import ApprovisionnementModel
from models.client_model import ClientModel
from models.produit_model import ProduitModel

class MagasinModel:
    collection = mongo.db.magasin

    @staticmethod
    def create_magasin(magasin_data, licence_data, admin_data):
        """
        Crée un nouveau magasin avec les informations détaillées et un compte admin associé.

        :param magasin_data: dict contenant 'denomination', 'pays', 'ville', 'quartier', 'email', 'activité'
        :param licence_data: dict contenant 'nombre_manager' et 'nombre_livreur'
        :param admin_data: dict contenant 'name', 'first_name' et 'email'
        :return: dict contenant les IDs du magasin et de l’admin
        """
        # Création du document magasin
        magasin = {
            "denomination": magasin_data["denomination"],
            "pays": magasin_data["pays"],
            "ville": magasin_data["ville"],
            "quartier": magasin_data["quartier"],
            "email": magasin_data["email"],
            "activité": magasin_data["activité"],
            "logo": magasin_data.get("logo"),

            "licence": {
                "max_managers": int(licence_data["nombre_manager"]),
                "max_livreurs": int(licence_data["nombre_livreur"]),
            },
            "created_by_staff": True,
            "is_active" : True,
            "created_at": datetime.utcnow()
        }

        # Insertion du magasin
        result = MagasinModel.collection.insert_one(magasin)
        magasin_id = str(result.inserted_id)

        # Création du compte admin du magasin
        admin_id = UserModel.create_admin(
            name=admin_data["name"],
            first_name=admin_data["first_name"],
            email=admin_data["email"],
            password=admin_data["password"],
            magasin_id=magasin_id,
            role="admin",
                
        )
        token = generate_validation_token(admin_id)
        # Envoi de l'email de changement de mot de passe à l'administrateur du magasin
        #send_validation_email(admin_data["email"], token)
        send_validation_email_creation_account(
            to_email=admin_data["email"],
            credentials={
                "name": admin_data["name"],
                "first_name": admin_data["first_name"],
                "role": "admin",
                "email": admin_data["email"],
                "password": admin_data["password"]
            }
        )


        return {
            "message": "Magasin et compte admin créés avec succès",
            "magasin_id": magasin_id,
            "admin_id": admin_id
        }
        
    # Vérifie si l'email du magasin existe déjà
    @staticmethod
    def get_magasin_by_email(email):
        """
        Récupère un magasin par son email.
        :param email: L'email du magasin.
        :return: Un dictionnaire contenant les informations du magasin.
        """
        magasin = MagasinModel.collection.find_one({"email": email})
        if magasin:
            magasin["_id"] = str(magasin["_id"])
        return magasin
    
    # récupère un magasin via l'email de l'administrateur
    # pour vérifier si l'email de l'administrateur existe déjà
    # dans la base de données avant de créer un nouveau magasin
    # et un compte admin associé
    @staticmethod
    def get_admin_by_email(email):
        """
        Récupère un magasin par l'email de l'administrateur.
        :param email: L'email de l'administrateur.
        :return: Un dictionnaire contenant les informations du magasin.
        """
        magasin = MagasinModel.collection.find_one({"admin.email": email})
        if magasin:
            magasin["_id"] = str(magasin["_id"])
        return magasin
        
    # Récupère un magasin via son ID
    @staticmethod
    def get_magasin_by_id(magasin_id):
        """
        Récupère un magasin par son ID.
        :param magasin_id: L'ID du magasin.
        :return: Un dictionnaire contenant les informations du magasin.
        """
        magasin = MagasinModel.collection.find_one({"_id": ObjectId(magasin_id)})
        if magasin:
            magasin["_id"] =str( magasin["_id"])  # On transforme l'ObjectId en chaîne pour l'utiliser dans l'API
            users = UserModel.collection.find({"magasin_id": ObjectId(magasin_id)})
            user_list = []
            for user in users:
                user["_id"] = str(user["_id"])
                user["magasin_id"] = str(user["magasin_id"])
                user_list.append(user)
            magasin["utilisateurs"] = user_list
        else:   
            magasin = None
        return magasin
    
    @staticmethod
    def update_magasin(magasin_id, update_data):
        """
        Met à jour les informations d'un magasin.
        :param magasin_id: L'ID du magasin à mettre à jour.
        :param update_data: Un dictionnaire contenant les données à mettre à jour.
        :return: Un dictionnaire contenant le message de succès ou d'erreur.
        """
        result = MagasinModel.collection.update_one(
            {"_id": ObjectId(magasin_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return {"message": "Magasin mis à jour avec succès."}
        else:
            return {"message": "Aucune mise à jour effectuée."}
        
    @staticmethod
    def delete_magasin(magasin_id):
        """
        Supprime un magasin par son ID.
        :param magasin_id: L'ID du magasin à supprimer.
        :return: Un dictionnaire contenant le message de succès ou d'erreur.
        """
        result = MagasinModel.collection.delete_one({"_id": ObjectId(magasin_id)})
        # récupérer tous les utilisateurs du magasin
        users = UserModel.collection.find({"magasin_id": ObjectId(magasin_id)})
        # supprimer tous les utilisateurs du magasin
        for user in users:
            UserModel.collection.delete_one({"_id": user["_id"]})
        # supprimer le magasin
        produits = ProduitModel.collection.find({"magasin_id": ObjectId(magasin_id)})
        # supprimer tous les produits du magasin
        for produit in produits:
            ProduitModel.collection.delete_one({"_id": produit["_id"]})
        
        from models.categorie_model import CategorieModel
        categories = CategorieModel.collection.find({"magasin_id": ObjectId(magasin_id)})
        # supprimer toutes les catégories du magasin
        for categorie in categories:
            CategorieModel.collection.delete_one({"_id": categorie["_id"]})
            
        clients = ClientModel.collection.find({"magasin_id": ObjectId(magasin_id)})
        # supprimer tous les clients du magasin
        for client in clients:
            ClientModel.collection.delete_one({"_id": client["_id"]})
        
            
    
        if result.deleted_count > 0:
            return {"message": "Magasin supprimé avec succès."}
        else:
            return {"message": "Magasin non trouvé."}
        
    
    
    
    
     #Retourne tous les magasins de la base de données avec les utilisateurs associés.
    
    @staticmethod
    def get_all_magasin():
        """
            Récupère tous les magasins avec les utilisateurs associés.
    :return: Une liste de dictionnaires contenant les informations de chaque magasin.   """
        magasins = MagasinModel.collection.find()
        result = []
        for magasin in magasins:
            magasin_id = magasin["_id"]
            users = UserModel.collection.find({"magasin_id": magasin_id})
            user_list = []
            for user in users:
                user["_id"] = str(user["_id"])
                user["magasin_id"] = str(user["magasin_id"])
                user_list.append(user)

            magasin["_id"] = str(magasin["_id"])
            magasin["utilisateurs"] = user_list
            result.append(magasin)
        return result    


    @staticmethod
    def toggle_magasin_status(magasin_id):
        """
        Change le statut d'un magasin (actif/inactif).
        :param magasin_id: L'ID du magasin à mettre à jour.
        :return: Un dictionnaire contenant le message de succès ou d'erreur.
        """
        magasin = MagasinModel.collection.find_one({"_id": ObjectId(magasin_id)})
        if not magasin:
            return {"message": "Magasin non trouvé."}
        
        new_status = not magasin.get("active", True)
        result = MagasinModel.collection.update_one(
            {"_id": ObjectId(magasin_id)},
            {"$set": {"active": new_status}}
        )
        
        if result.modified_count > 0:
            return {"message": "Statut du magasin mis à jour avec succès."}
        else:
            return {"message": "Aucune mise à jour effectuée."}
        
    @staticmethod
    def search_magasins(search_query=None, pays=None, ville=None, quartier=None):
        """
        Recherche et filtre les magasins selon plusieurs critères.
        
        :param search_query: Texte de recherche pour la dénomination (optionnel)
        :param pays: Filtre par pays (optionnel)
        :param ville: Filtre par ville (optionnel)
        :param quartier: Filtre par quartier (optionnel)
        :return: Une liste de dictionnaires contenant les magasins filtrés avec leurs utilisateurs
        """
        # Construction du filtre dynamique
        filter_query = {}
        
        # Recherche textuelle sur la dénomination (insensible à la casse)
        if search_query:
            filter_query["denomination"] = {"$regex": search_query, "$options": "i"}
        
        # Filtres exacts sur les champs géographiques
        if pays:
            filter_query["pays"] = {"$regex": pays, "$options": "i"}
        
        if ville:
            filter_query["ville"] = {"$regex": ville, "$options": "i"}
        
        if quartier:
            filter_query["quartier"] = {"$regex": quartier, "$options": "i"}
        
        # Exécution de la requête
        magasins = MagasinModel.collection.find(filter_query)
        result = []
        
        for magasin in magasins:
            magasin_id = magasin["_id"]
            
            # Récupération des utilisateurs associés
            users = UserModel.collection.find({"magasin_id": magasin_id})
            user_list = []
            for user in users:
                user["_id"] = str(user["_id"])
                user["magasin_id"] = str(user["magasin_id"])
                user_list.append(user)
            
            # Conversion de l'ID et ajout des utilisateurs
            magasin["_id"] = str(magasin["_id"])
            magasin["utilisateurs"] = user_list
            result.append(magasin)
        
        return result
        
