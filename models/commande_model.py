# models/commande_model.py

from bson import ObjectId
from datetime import datetime
from extensions import mongo


class CommandeModel:
    collection = mongo.db.commandes

    @staticmethod
    def create_commande(data):
        """Crée une nouvelle commande avec les champs requis."""

        commande = {
            "client_id": ObjectId(data["client_id"]),
            "magasin_id": ObjectId(data["magasin_id"]),
            "produits": data.get("produits", []),  # Liste de dicts {id, nom, quantité, prix}
            "montant_total": data.get("montant_total", 0.0),
            "statut": data.get("statut", "en_attente"),
            "adresse_livraison": data.get("adresse_livraison", ""),
            "date_commande": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = CommandeModel.collection.insert_one(commande)
        return str(result.inserted_id)

    @staticmethod
    def get_by_id(commande_id):
        return CommandeModel.collection.find_one({"_id": ObjectId(commande_id)})

    @staticmethod
    def get_all_by_magasin(magasin_id):
        return list(CommandeModel.collection.find({"magasin_id": ObjectId(magasin_id)}))

    @staticmethod
    def update_commande(commande_id, data):
        data["updated_at"] = datetime.utcnow()
        CommandeModel.collection.update_one(
            {"_id": ObjectId(commande_id)},
            {"$set": data}
        )
        return True

    @staticmethod
    def delete_commande(commande_id):
        CommandeModel.collection.delete_one({"_id": ObjectId(commande_id)})
        return True
    
    # récupérer toutes les commandes d'un client
    @staticmethod
    def get_commandes_by_client(client_id):
        return list(CommandeModel.collection.find({"client_id": ObjectId(client_id)}))
