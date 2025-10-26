from datetime import datetime
from bson import ObjectId
from extensions import mongo
from models.user_model import UserModel
from utils.jwt_token import generate_validation_token
from utils.email import send_validation_email, send_validation_email_creation_account
 
 

class ChurchModel:
    collection = mongo.db.church

    @staticmethod
    def create_church(church_data, licence_data, admin_data):
        """
        Crée un nouveau church avec les informations détaillées et un compte admin associé.

        :param church_data: dict contenant 'denomination', 'pays', 'ville', 'quartier', 'email', 'activité'
        :param licence_data: dict contenant 'nombre_manager' et 'nombre_livreur'
        :param admin_data: dict contenant 'name', 'first_name' et 'email'
        :return: dict contenant les IDs du church et de l’admin
        """
        # Création du document church
        church = {
            "denomination": church_data["denomination"],
            "pays": church_data["pays"],
            "ville": church_data["ville"],
            "quartier": church_data["quartier"],
            "email": church_data["email"],
            "activité": church_data["activité"],
            "logo": church_data.get("logo"),

            "licence": {
                "max_managers": int(licence_data["nombre_manager"]),
                "max_livreurs": int(licence_data["nombre_livreur"]),
            },
            "created_by_staff": True,
            "is_active" : True,
            "created_at": datetime.utcnow()
        }

        # Insertion du church
        result = ChurchModel.collection.insert_one(church)
        church_id = str(result.inserted_id)

        # Création du compte admin du church
        admin_id = UserModel.create_admin(
            name=admin_data["name"],
            first_name=admin_data["first_name"],
            email=admin_data["email"],
            password=admin_data["password"],
            church_id=church_id,
            role="admin",
                
        )
        token = generate_validation_token(admin_id)
        # Envoi de l'email de changement de mot de passe à l'administrateur du church
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
            "message": "church et compte admin créés avec succès",
            "church_id": church_id,
            "admin_id": admin_id
        }
        
    # Vérifie si l'email du church existe déjà
    @staticmethod
    def get_church_by_email(email):
        """
        Récupère un church par son email.
        :param email: L'email du church.
        :return: Un dictionnaire contenant les informations du church.
        """
        church = ChurchModel.collection.find_one({"email": email})
        if church:
            church["_id"] = str(church["_id"])
        return church
    
    # récupère un church via l'email de l'administrateur
    # pour vérifier si l'email de l'administrateur existe déjà
    # dans la base de données avant de créer un nouveau church
    # et un compte admin associé
    @staticmethod
    def get_admin_by_email(email):
        """
        Récupère un church par l'email de l'administrateur.
        :param email: L'email de l'administrateur.
        :return: Un dictionnaire contenant les informations du church.
        """
        church = ChurchModel.collection.find_one({"admin.email": email})
        if church:
            church["_id"] = str(church["_id"])
        return church
        
    # Récupère un church via son ID
    @staticmethod
    def get_church_by_id(church_id):
        """
        Récupère un church par son ID.
        :param church_id: L'ID du church.
        :return: Un dictionnaire contenant les informations du church.
        """
        church = ChurchModel.collection.find_one({"_id": ObjectId(church_id)})
        if church:
            church["_id"] =str( church["_id"])  # On transforme l'ObjectId en chaîne pour l'utiliser dans l'API
            users = UserModel.collection.find({"church_id": ObjectId(church_id)})
            user_list = []
            for user in users:
                user["_id"] = str(user["_id"])
                user["church_id"] = str(user["church_id"])
                user_list.append(user)
            church["utilisateurs"] = user_list
        else:   
            church = None
        return church
    
    @staticmethod
    def update_church(church_id, update_data):
        """
        Met à jour les informations d'un church.
        :param church_id: L'ID du church à mettre à jour.
        :param update_data: Un dictionnaire contenant les données à mettre à jour.
        :return: Un dictionnaire contenant le message de succès ou d'erreur.
        """
        result = ChurchModel.collection.update_one(
            {"_id": ObjectId(church_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return {"message": "church mis à jour avec succès."}
        else:
            return {"message": "Aucune mise à jour effectuée."}
        
    @staticmethod
    def delete_church(church_id):
        """
        Supprime un church par son ID.
        :param church_id: L'ID du church à supprimer.
        :return: Un dictionnaire contenant le message de succès ou d'erreur.
        """
        result = ChurchModel.collection.delete_one({"_id": ObjectId(church_id)})
        # récupérer tous les utilisateurs du church
        users = UserModel.collection.find({"church_id": ObjectId(church_id)})
        # supprimer tous les utilisateurs du church
        for user in users:
            UserModel.collection.delete_one({"_id": user["_id"]})
        
        
        from models.categorie_model import CategorieModel
        categories = CategorieModel.collection.find({"church_id": ObjectId(church_id)})
        # supprimer toutes les catégories du church
        for categorie in categories:
            CategorieModel.collection.delete_one({"_id": categorie["_id"]})
            
       
            
    
        if result.deleted_count > 0:
            return {"message": "church supprimé avec succès."}
        else:
            return {"message": "church non trouvé."}
        
    
    
    
    
     #Retourne tous les churchs de la base de données avec les utilisateurs associés.
    
    @staticmethod
    def get_all_church():
        """
            Récupère tous les churchs avec les utilisateurs associés.
    :return: Une liste de dictionnaires contenant les informations de chaque church.   """
        churchs = ChurchModel.collection.find()
        result = []
        for church in churchs:
            church_id = church["_id"]
            users = UserModel.collection.find({"church_id": church_id})
            user_list = []
            for user in users:
                user["_id"] = str(user["_id"])
                user["church_id"] = str(user["church_id"])
                user_list.append(user)

            church["_id"] = str(church["_id"])
            church["utilisateurs"] = user_list
            result.append(church)
        return result    


    @staticmethod
    def toggle_church_status(church_id):
        """
        Change le statut d'un church (actif/inactif).
        :param church_id: L'ID du church à mettre à jour.
        :return: Un dictionnaire contenant le message de succès ou d'erreur.
        """
        church = ChurchModel.collection.find_one({"_id": ObjectId(church_id)})
        if not church:
            return {"message": "church non trouvé."}
        
        new_status = not church.get("active", True)
        result = ChurchModel.collection.update_one(
            {"_id": ObjectId(church_id)},
            {"$set": {"active": new_status}}
        )
        
        if result.modified_count > 0:
            return {"message": "Statut du church mis à jour avec succès."}
        else:
            return {"message": "Aucune mise à jour effectuée."}
        
    @staticmethod
    def search_churchs(search_query=None, pays=None, ville=None, quartier=None):
        """
        Recherche et filtre les churchs selon plusieurs critères.
        
        :param search_query: Texte de recherche pour la dénomination (optionnel)
        :param pays: Filtre par pays (optionnel)
        :param ville: Filtre par ville (optionnel)
        :param quartier: Filtre par quartier (optionnel)
        :return: Une liste de dictionnaires contenant les churchs filtrés avec leurs utilisateurs
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
        churchs = ChurchModel.collection.find(filter_query)
        result = []
        
        for church in churchs:
            church_id = church["_id"]
            
            # Récupération des utilisateurs associés
            users = UserModel.collection.find({"church_id": church_id})
            user_list = []
            for user in users:
                user["_id"] = str(user["_id"])
                user["church_id"] = str(user["church_id"])
                user_list.append(user)
            
            # Conversion de l'ID et ajout des utilisateurs
            church["_id"] = str(church["_id"])
            church["utilisateurs"] = user_list
            result.append(church)
        
        return result
        
