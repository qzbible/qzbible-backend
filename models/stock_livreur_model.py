# models/stock_livreur_model.py

from bson import ObjectId
from datetime import datetime
from extensions import mongo


"""
Ce modèle permet de gérer les produits disponibles dans le stock d’un livreur.

Il permet d’ajouter ou retirer des quantités, ainsi que de récupérer la liste ou une quantité spécifique d’un produit.

Lorsqu’un livreur fait une livraison, les quantités sont diminuées ici, et le stock du magasin avait déjà été diminué lors de l’approvisionnement.
"""

class StockLivreurModel:
    #
   
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.stocks_livreur
    
    collection = mongo.db.stocks_livreur
    
    
    @staticmethod
    def ajouter_produit(livreur_id, produit_id, quantite):
        stock_existant = StockLivreurModel.get_collection().find_one({
            "livreur_id": ObjectId(livreur_id),
            "produit_id": ObjectId(produit_id)
        })

        if stock_existant:
            nouvelle_quantite = stock_existant["quantite"] + quantite
            return StockLivreurModel.get_collection().find_one_and_update(
                {"_id": stock_existant["_id"]},
                {"$set": {"quantite": nouvelle_quantite, "updated_at": datetime.utcnow()}}
            )
        else:
            stock = {
                "livreur_id": ObjectId(livreur_id),
                "produit_id": ObjectId(produit_id),
                "quantite": quantite,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = StockLivreurModel.get_collection().insert_one(stock)
            return StockLivreurModel.get_collection().find_one({"_id": result.inserted_id})

    # Retirer une quantité de produit du stock d'un livreur
    @staticmethod
    def retirer_produit(livreur_id, produit_id, quantite):
        stock = StockLivreurModel.get_collection().find_one({
            "livreur_id": ObjectId(livreur_id),
            "produit_id": ObjectId(produit_id)
        })

        if not stock or stock["quantite"] < quantite:
            return None  # Pas assez de stock ou inexistant

        nouvelle_quantite = stock["quantite"] - quantite
        if nouvelle_quantite == 0:
            # Supprimer l'entrée si stock vide
            StockLivreurModel.get_collection().delete_one({"_id": stock["_id"]})
            return None
        else:
            return StockLivreurModel.get_collection().find_one_and_update(
                {"_id": stock["_id"]},
                {"$set": {"quantite": nouvelle_quantite, "updated_at": datetime.utcnow()}}
            )

# Récupérer tous les produits du stock d'un livreur
    @staticmethod
    def get_stock_livreur(livreur_id):
        return list(
            StockLivreurModel.get_collection().find(
                {"livreur_id": ObjectId(livreur_id)}
            ).sort("updated_at", -1)  #Tri décroissant par date de mise à jour
        )
    
    # Retourner tous les produits du stock et supprimer le stock du livreur
    @staticmethod
    def get_all_stock_livreur(livreur_id):
        stocks = StockLivreurModel.get_stock_livreur(livreur_id)
        StockLivreurModel.get_collection().delete_many({"livreur_id": ObjectId(livreur_id)})
        return stocks
    
        
    @staticmethod
    def get_produit_quantite(livreur_id, produit_id):
        stock = StockLivreurModel.get_collection().find_one({
            "livreur_id": ObjectId(livreur_id),
            "produit_id": ObjectId(produit_id)
        })
        return stock["quantite"] if stock else 0
    
    # Retitrer des produit livré du stock du livreur

    @staticmethod
    def retirer_stock(livreur_id, produits):
        for produit in produits:
            StockLivreurModel.get_collection().update_one(
                {
                    "livreur_id": ObjectId(livreur_id),
                    "produit_id": ObjectId(produit["produit_id"])
                },
                {
                    "$inc": {"quantite": -int(produit["quantite"])}
                }
            )
            
            
    # Ajouter des produits approvisionnés par le manager ou l'admin dans le stock du livreur      
    @staticmethod
    def ajouter_stock(livreur_id, produits):
        for produit in produits:
            StockLivreurModel.get_collection().update_one(
                {
                    "livreur_id": ObjectId(livreur_id),
                    "produit_id": ObjectId(produit["produit_id"])
                },
                {
                    "$inc": {"quantite": int(produit["quantite"])},
                    "$setOnInsert": {
                        "created_at": datetime.utcnow()
                    },
                    "$set": {
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True  #  Important pour insérer si non existant
            )

    # reduire le stock du livreur des produits de l'approvisionnement supprimé.
    @staticmethod
    def retirer_du_stock(livreur_id, produit_id, quantite):
        """
        Réduit la quantité du stock du livreur pour un produit donné.
        Si la quantité devient 0, supprime le document.
        """
        filtre = {
            "livreur_id": ObjectId(livreur_id),
            "produit_id": ObjectId(produit_id)
        }

        stock = StockLivreurModel.get_collection().find_one(filtre)

        if not stock:
            raise Exception(f"Produit {produit_id} non trouvé dans le stock du livreur {livreur_id}")

        nouvelle_quantite = stock["quantite"] - quantite

        if nouvelle_quantite < 0:
            raise Exception(f"Stock insuffisant pour le produit {produit_id} chez le livreur {livreur_id}")

        if nouvelle_quantite == 0:
            StockLivreurModel.get_collection().delete_one({"_id": stock["_id"]})
        else:
            StockLivreurModel.get_collection().update_one(
                {"_id": stock["_id"]},
                {"$set": {"quantite": nouvelle_quantite}}
            )



