# models/approvisionnement_model.py

from bson import ObjectId
from datetime import datetime
from extensions import mongo

"""
Lorsqu’un admin ou manager approvisionne un livreur, un document est enregistré ici avec :

    l’admin_id ou manager_id

    le livreur_id

    la liste des produits avec leurs quantités

Ce modèle permet aussi de retrouver tous les approvisionnements d’un livreur, ou un approvisionnement en particulier.
"""

class ApprovisionnementModel:
    collection = mongo.db.approvisionnements

    @staticmethod
    def enregistrer_approvisionnement(data):
        approvisionnement = {
            "magasin_id": ObjectId(data["magasin_id"]),
            "admin_id": ObjectId(data["admin_id"]),  # ou manager_id
            "livreur_id": ObjectId(data["livreur_id"]),
            "produits": [
                {
                    "produit_id": ObjectId(item["produit_id"]),
                    "quantite": int(item["quantite"])
                } for item in data["produits"]
            ],
            "created_at": datetime.utcnow()
        }

        result = ApprovisionnementModel.collection.insert_one(approvisionnement)
        return str(result.inserted_id)

    @staticmethod
    def get_all_by_livreur(livreur_id):
        return list(ApprovisionnementModel.collection.find({
            "livreur_id": ObjectId(livreur_id)
        }))
    
    @staticmethod
    def get_all_by_manager(admin_id):
        return list(ApprovisionnementModel.collection.find({
            "admin_id" : ObjectId(admin_id)
        }))

    @staticmethod
    def get_by_id(approvisionnement_id):
        return ApprovisionnementModel.collection.find_one({
            "_id": ObjectId(approvisionnement_id)
        })


