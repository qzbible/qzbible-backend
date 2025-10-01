from bson import ObjectId
from models.stock_livreur_model import StockLivreurModel
from models.produit_model import ProduitModel
from models.categorie_model import CategorieModel
from flask import request


def get_stock_par_categorie_pour_livreur(livreur_id):
    # Récupération triée des stocks du livreur
    stocks = StockLivreurModel.collection.find(
        {"livreur_id": ObjectId(livreur_id)}
    ).sort("updated_at", -1)  # ✅ tri du plus récent au plus ancien

    produits_par_categorie = {}

    for stock in stocks:
        produit = ProduitModel.get_by_id(ObjectId(stock["produit_id"]))
        if not produit:
            continue

        produit["_id"] = str(produit["_id"])
        produit["categorie_id"] = str(produit["categorie_id"])
        produit["quantite_livreur"] = stock["quantite"]
        produit['image'] = f"{request.host_url}uploads/images/{produit['image']}" if produit.get("image") else None

        if "mouvements_stock" in produit:
            del produit["mouvements_stock"]

        categorie_id = produit["categorie_id"]
        if categorie_id not in produits_par_categorie:
            categorie = CategorieModel.get_by_id(categorie_id)
            if not categorie:
                continue
            categorie["_id"] = str(categorie["_id"])
            categorie["produits"] = []

            produits_par_categorie[categorie_id] = categorie

        produits_par_categorie[categorie_id]["produits"].append(produit)

    return list(produits_par_categorie.values())

# Récupérer les produits d'un livreur présent dans le stock
# services/livreur_services.py

def get_stock_livreur_avec_details(livreur_id):
    from models.stock_livreur_model import StockLivreurModel
    from models.produit_model import ProduitModel
    from models.categorie_model import CategorieModel

    stocks = StockLivreurModel.collection.find({"livreur_id": ObjectId(livreur_id)}).sort("updated_at", -1)

    produits_formattés = []

    for stock in stocks:
        produit = ProduitModel.get_by_id(stock["produit_id"])
        if not produit:
            continue

        # Quantité actuelle détenue par le livreur
        quantite = stock.get("quantite", 0)

        # Détermination de l'état
        etat = "en stock" if quantite > 0 else "en rupture"

        # Récupérer la catégorie
        categorie_id = produit.get("categorie_id")
        categorie_nom = "Inconnu"
        if categorie_id:
            categorie = CategorieModel.get_by_id(categorie_id)
            if categorie:
                categorie_nom = categorie.get("nom", "Inconnu")
            categorie_id = str(categorie_id)

        # Construction du produit formaté
        produit_formatté = {
            "_id": str(produit["_id"]),
            "nom": produit.get("nom"),
            "description": produit.get("description"),
            "image": f"{request.host_url}uploads/images/{produit['image']}" if produit.get("image") else None,
            "prix": produit.get("prix") ,
            "unite": produit.get("unite"),
            "quantite": quantite,
            "quantite_initiale": quantite,
            "etat": etat,
            "categorie_id": categorie_id,
            "magasin_id": str(produit.get("magasin_id")),
            "created_at": produit.get("created_at"),
            "categorie_nom": categorie_nom
        }
        print(f"image : {produit_formatté['image']}")

        produits_formattés.append(produit_formatté)
    
    # Filtrer les produits par date de création
    produits_formattés.sort(key=lambda x: x.get("updated_at", ""))

    return produits_formattés
