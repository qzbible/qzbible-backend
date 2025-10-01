# models/categorie_model.py
from datetime import datetime
from bson import ObjectId
from models.magasin_model import MagasinModel
from extensions import mongo
from rapidfuzz import fuzz
from utils.inject_magasin_id import inject_magasin_id


class CategorieModel:
    collection = mongo.db.categories

    @staticmethod
    def create_categorie(data):
        """
        Crée une nouvelle catégorie avec les informations fournies.
        
        :param data: dict contenant 'name', 'description', 'magasin_id'
        :return: dict contenant le message de succès et l'ID de la catégorie créée
        """
        
        # s'asser que la catégorie qu'on veut créer n'existe pas déjà
        categorie_existant = CategorieModel.collection.find_one({
            "nom": data["nom"],
            "magasin_id": ObjectId(data["magasin_id"])
        })
        if categorie_existant:
            return {
                "error": "Cette catégorie exite déjà existe déjà dans ce magasin"
            }, 409  # 409 Conflict

        magasin = MagasinModel.collection.find_one({"_id": ObjectId(data["magasin_id"])})
        if not magasin:
            return {"message": "Magasin non trouvé"}, 404
        categorie = {
            "nom": data["nom"],
            "description": data["description"],
            "magasin_id": ObjectId(data["magasin_id"]),
            "created_at": datetime.utcnow()
        }
        
        result = CategorieModel.collection.insert_one(categorie)
        
        return {
            "message": "Catégorie créée avec succès",
            "categorie_id": str(result.inserted_id)
        }
        
    @staticmethod
    def get_all_by_magasin(magasin_id):
        """
        Récupère toutes les catégories d'un magasin donné.
        
        :param magasin_id: ID du magasin
        :return: Liste de dictionnaires contenant les informations de chaque catégorie
        """
        categories = CategorieModel.collection.find({"magasin_id": ObjectId(magasin_id)})
        #return [categorie for categorie in categories]
        return list(categories)
    
    @staticmethod
    def get_categorie_by_id(categorie_id):
        """
        Récupère une catégorie par son ID.
        
        :param categorie_id: ID de la catégorie
        :return: Dictionnaire contenant les informations de la catégorie
        """
        categorie = CategorieModel.collection.find_one({"_id": ObjectId(categorie_id)})
        if categorie:
            categorie["_id"] = str(categorie["_id"])
        return categorie
    
    
    @staticmethod
    def get_by_id(categorie_id):
        """
        Récupère une catégorie par son ID.
        
        :param categorie_id: ID de la catégorie
        :return: Dictionnaire contenant les informations de la catégorie
        """
        categorie = CategorieModel.collection.find_one({"_id": ObjectId(categorie_id)})
        if categorie:
            categorie["_id"] = str(categorie["_id"])
        return categorie
    
    @staticmethod
    def update_categorie(categorie_id, data):
        """
        Met à jour une catégorie existante.
        
        :param categorie_id: ID de la catégorie à mettre à jour
        :param data: dict contenant les nouvelles informations
        :return: bool indiquant si la mise à jour a réussi
        """
        result = CategorieModel.collection.update_one(
            {"_id": ObjectId(categorie_id)},
            {"$set": data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete_categorie(categorie_id):
        """
        Supprime une catégorie par son ID.
        
        :param categorie_id: ID de la catégorie à supprimer
        :return: bool indiquant si la suppression a réussi
        """
        result = CategorieModel.collection.delete_one({"_id": ObjectId(categorie_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def get_all():
        return list(CategorieModel.collection.find({}))
    
    @staticmethod
    def find_best_match(nom, seuil=80):
        nom = nom.lower()
        categories = CategorieModel.get_all()
        matches = [
            (fuzz.ratio(nom, cat["nom"].lower()), cat)
            for cat in categories
        ]
        matches = [m for m in matches if m[0] >= seuil]
        if matches:
            return str(matches[0][1]["_id"])
        return None

    @staticmethod
    def create_if_not_exists(nom_categorie):
        nom = nom_categorie.strip()
        existing = CategorieModel.collection.find_one({"nom": {"$regex": f"^{nom}$", "$options": "i"}})
        if existing:
            return str(existing["_id"])
        # Crée une nouvelle catégorie si elle n'existe pas et injecter l'id du magasin
        data = {}
        data = inject_magasin_id(data)
        nouvelle_categorie = {
            "magasin_id": ObjectId(data['magasin_id']),  # Remplacer par l'ID du magasin approprié
            "nom": nom,
            "description": f"Catégorie auto-créée lors d’un import Excel",
            "created_at": datetime.utcnow(),
        }
        result = CategorieModel.collection.insert_one(nouvelle_categorie)
        return str(result.inserted_id)