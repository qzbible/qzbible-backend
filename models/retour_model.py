# models/retour_model.py

from datetime import datetime
from bson import ObjectId
from extensions import mongo

class RetourLivraisonModel:
    #
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.retours_livraison
    
    collection = mongo.db.retours_livraison
    
    @staticmethod
    def enregistrer_retour(data):
        retour = {
            "livraison_id": ObjectId(data["livraison_id"]),
            "produits": data["produits"],
            "motif": data.get("motif", ""),
            "manager_id": ObjectId(data["manager_id"]) if data.get("manager_id") else None,
            "livreur_id": ObjectId(data["livreur_id"]) if data.get("livreur_id") else None,
            "created_at": datetime.utcnow()
        }
        result = RetourLivraisonModel.get_collection().insert_one(retour)
        return str(result.inserted_id)
    
    @staticmethod
    def get_retours_by_livraison(livraison_id):
        return list(RetourLivraisonModel.get_collection().find({"livraison_id": ObjectId(livraison_id)}))
