# services/produit_services.py
from werkzeug.utils import secure_filename
import os
from models.produit_model import ProduitModel
from flask import current_app
from models.categorie_model import CategorieModel
from models.livraison_model import LivraisonModel
from bson import ObjectId
from models.produit_model import ProduitModel
from flask import request

# Créer ou enregister un nouveau produit
def create_produit_service(data, image_file):
    image_filename = None
    if image_file:
        filename = secure_filename(image_file.filename)
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        # Vérifier si le dossier d'upload existe, sinon le créer
        os.makedirs(upload_dir, exist_ok=True)
        image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        image_file.save(image_path)
        image_filename = filename
    
    produit_id = ProduitModel.create_produit(data, image_filename)
    return {"message": "Produit créé", "produit_id": produit_id}, 201



# Récupérer tous les produits d'un magasin
def get_produits_by_magasin_service(magasin_id, filters=None):
    if isinstance(magasin_id, dict) and "$oid" in magasin_id:
        magasin_id = magasin_id["$oid"]

    produits = ProduitModel.get_all_by_magasin(magasin_id)
    # Tri par date de mise à jour, du plus récent au plus ancien
    produits.sort(
        key=lambda x: x.get("updated_at") or x.get("created_at"),
        reverse=True
    )    
    result = []

    for produit in produits:
        produit.pop("mouvements_stock", None)
        
        categorie_id = produit.get("categorie_id")
        categorie_nom = "Inconnu"
        if categorie_id:
            categorie = CategorieModel.get_categorie_by_id(categorie_id)
            if categorie:
                categorie_nom = categorie.get("nom", "Inconnu")
        produit["categorie_nom"] = categorie_nom

        produit["image_url"] = (
            f"{request.host_url}uploads/images/{produit['image']}"
            if produit.get("image") else None
        )

        # Application des filtres
        if filters:
            if filters["nom"] and filters["nom"].lower() not in produit["nom"].lower():
                continue
            if filters["etat"] and produit.get("etat") != filters["etat"]:
                continue
            if filters["categorie_nom"] and filters["categorie_nom"].lower() not in categorie_nom.lower():
                continue
            if filters["prix_min"] and produit.get("prix", 0) < filters["prix_min"]:
                continue
            if filters["prix_max"] and produit.get("prix", 0) > filters["prix_max"]:
                continue
            if filters["quantite_min"] and produit.get("quantite", 0) < filters["quantite_min"]:
                continue
            if filters["quantite_max"] and produit.get("quantite", 0) > filters["quantite_max"]:
                continue

        result.append(produit)
        # retourner les produits par ordre de récent
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return result



## Mettre à jour un produit
def update_produit_service(produit_id, data, image_file=None):
    # Récupérer l'état actuel du produit
    produit_avant = ProduitModel.get_by_id(produit_id)
    if not produit_avant:
        return {"error": "Produit non trouvé"}, 404
    
    ancienne_quantite = produit_avant["quantite"]  #  Stock actuel
    print(f"Ancienne quantité : {ancienne_quantite}")
    # Transformer la quantité en entier si elle est présente
    if "quantite" in data and data["quantite"] is not None:
        try:
            data["quantite"] = int(data["quantite"])
        except ValueError:
            return {"error": "La quantité doit être un entier"}, 400
    # Valider la nouvelle quantité si présente
    if "quantite" in data and data["quantite"] is not None:
        if data["quantite"] < 0:
            return {"error": "La quantité doit être un entier positif"}, 400

    # Traitement de l'image si fournie
    if image_file:
        filename = secure_filename(image_file.filename)
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        # Vérifier si le dossier d'upload existe, sinon le créer
        os.makedirs(upload_dir, exist_ok=True)
        image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        image_file.save(image_path)
        data["image"] = filename


    # Appliquer la mise à jour sur la base
    ProduitModel.update_produit(produit_id, data)
    produit_apres = ProduitModel.get_by_id(produit_id)

    # Vérifier si la quantité a changé et est supérieure à l'ancienne
    nouvelle_quantite = data.get("quantite", ancienne_quantite)

    if nouvelle_quantite > ancienne_quantite:
        increment = nouvelle_quantite - ancienne_quantite

        # Préparer l'acteur pour le mouvement
        acteur = {"admin_id": data.get("admin_id", None)}

        # Ajouter le mouvement de stock
        ProduitModel.increment_stock(
            produit_id=produit_id,
            quantite=increment,
            acteur=acteur,
            type_mouvement="modification_produit"
        )

    return {
        "message": "Produit mis à jour avec succès",
        "produit": produit_apres
    }, 200



# Supprimer un produit
def delete_produit_service(produit_id):
    try:
        result = ProduitModel.delete_mouvements_stock(produit_id)
        if not result:
            return {"error": "Produit non trouvé ou erreur lors de la suppression des mouvements de stock"}, 404
    except Exception as e:
        return {"error": f"Erreur lors de la suppression des mouvements de stock : {str(e)}"}, 500
    
    return ProduitModel.delete_produit(produit_id)




# Récupérer un produit par son ID
def get_produit_by_id_service(produit_id):
    produit =  ProduitModel.get_by_id(produit_id)
    produit['image'] = f"{request.host_url}uploads/images/{produit['image']}" if produit.get("image") else None
    return produit





# Récupérer les mouvements de stock d'un produit
def get_mouvements_stock_service(produit_id, type_mouvement=None):
    try:
        mouvements = ProduitModel.get_mouvements_stock(produit_id, type_mouvement)
        return {"mouvements": mouvements}, 200
    except Exception as e:
        return {"message": f"Erreur serveur : {str(e)}"}, 500




# Statistiques livreur

def get_meilleurs_produits_livreur(livreur_id):
    """
    Retourne les meilleurs produits livrés par un livreur donné,
    triés par quantité totale livrée (du plus vendu au moins vendu).
    Ainsi que : 
    - quantité totale livrée par produit
    - montant total généré par produit
    - pourcentage basé sur la quantité
    - pourcentage basé sur le montant
    
    """
    # 1. Récupérer toutes les livraisons faites par le livreur

    livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)

    # 2. Agréger les produits livrés
    stats = {}
    
    total_quantite = 0
    total_montant = 0  

    for livraison in livraisons:
        produits = livraison.get("produits", [])
        for produit in produits:
            produit_id = str(produit["produit_id"])
            quantite = produit.get("quantite", 0)
            prix_unitaire = produit.get("prix", 0)
            montant = quantite * prix_unitaire
            
            if produit_id not in stats:
                stats[produit_id] = {
                    "produit_id": produit_id,
                    "nom": produit.get("nom", ""),  # Peut être vide si non inclus dans la livraison
                    "quantite_totale": 0,
                    "montant_total": 0
                }

            stats[produit_id]["quantite_totale"] += quantite
            stats[produit_id]["montant_total"] += montant
            
            total_quantite += quantite
            total_montant += montant
            
    # 3. Compléter les infos des produits s'il en manque (optionnel mais recommandé)
    produit_ids = list(stats.keys())
    produits_info = ProduitModel.get_produits_by_ids(produit_ids)

    for produit in produits_info:
        pid = str(produit["_id"])
        if pid in stats:
            stats[pid]["nom"] = produit.get("nom", stats[pid]["nom"])
            quantite_totale = stats[pid]["quantite_totale"]
            montant_total = stats[pid]["montant_total"]
            
            stats[pid]["prix"] = produit.get("prix", 0)
            
            stats[pid]["pourcentage_quantite"] = round((quantite_totale / total_quantite) * 100, 2) if total_quantite else 0
            stats[pid]["pourcentage_montant"] = round((montant_total / total_montant) * 100, 2) if total_montant else 0
    # 4. Retourner la liste triée par quantité descendante
    return sorted(stats.values(), key=lambda x: x["montant_total"], reverse=True)[:5]





# Statistiques manager

def get_meilleurs_produits_total(livreur_id=None):
    """
    Retourne les meilleurs produits livrés (tous les livreurs ou un seul),
    triés par quantité totale livrée (du plus vendu au moins vendu).
    Ainsi que : 
    - quantité totale livrée par produit
    - montant total généré par produit
    - pourcentage basé sur la quantité
    - pourcentage basé sur le montant
    
    """
    # 1. Récupérer toutes les livraisons faites dans tout le magasin
    if livreur_id:
        livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)
    else:
        livraisons = LivraisonModel.get_all_livraisons()

    # 2. Agréger les produits livrés
    stats = {}
    
    total_quantite = 0
    total_montant = 0  

    for livraison in livraisons:
        produits = livraison.get("produits", [])
        for produit in produits:
            produit_id = str(produit["produit_id"])
            quantite = produit.get("quantite", 0)
            prix_unitaire = produit.get("prix", 0)
            montant = quantite * prix_unitaire
            
            if produit_id not in stats:
                stats[produit_id] = {
                    "produit_id": produit_id,
                    "nom": produit.get("nom", ""),  # Peut être vide si non inclus dans la livraison
                    "quantite_totale": 0,
                    "montant_total": 0
                }

            stats[produit_id]["quantite_totale"] += quantite
            stats[produit_id]["montant_total"] += montant
            
            total_quantite += quantite
            total_montant += montant
            
    # 3. Compléter les infos des produits s'il en manque (optionnel mais recommandé)
    produit_ids = list(stats.keys())
    produits_info = ProduitModel.get_produits_by_ids(produit_ids)

    for produit in produits_info:
        pid = str(produit["_id"])
        if pid in stats:
            stats[pid]["nom"] = produit.get("nom", stats[pid]["nom"])
            quantite_totale = stats[pid]["quantite_totale"]
            montant_total = stats[pid]["montant_total"]
            
            stats[pid]["prix"] = produit.get("prix", 0)
            
            stats[pid]["pourcentage_quantite"] = round((quantite_totale / total_quantite) * 100, 2) if total_quantite else 0
            stats[pid]["pourcentage_montant"] = round((montant_total / total_montant) * 100, 2) if total_montant else 0
    # 4. Retourner la liste triée par quantité descendante
    return sorted(stats.values(), key=lambda x: x["montant_total"], reverse=True)[:5]


# Retourne tous les produits d'un magasin, regroupés par catégorie
def get_stock_par_categorie_total(data):
    produits = ProduitModel.get_all_by_magasin(data["magasin_id"])  # Ce sont directement des produits
    produits_par_categorie = {}

    for produit in produits:
        produit["_id"] = str(produit["_id"])
        produit["categorie_id"] = str(produit["categorie_id"])
        produit["quantite_magasin"] = produit["quantite"]  # Renomme pour clarté
        produit['image'] = f"{request.host_url}uploads/images/{produit['image']}" if produit.get("image") else None

        #  Suppression des mouvements de stock
        if "mouvements_stock" in produit:
            del produit["mouvements_stock"]

        categorie_id = produit["categorie_id"]
        if categorie_id not in produits_par_categorie:
            categorie = CategorieModel.get_categorie_by_id(categorie_id)
            if not categorie:
                continue
            categorie["_id"] = str(categorie["_id"])
            categorie["produits"] = []

            produits_par_categorie[categorie_id] = categorie

        produits_par_categorie[categorie_id]["produits"].append(produit)

    return list(produits_par_categorie.values())


# approvisionner un produit dans le stock du magasin
def approvisionner_produit_service(produit_id, data):
    try:
        quantite = int(data["quantite"])
        admin_id = data.get("admin_id")

        acteur = {"admin_id": admin_id} if admin_id else {}

        produit = ProduitModel.approvisionner_produit(produit_id, quantite, acteur)

        if not produit:
            return {"error": "Produit non trouvé"}, 404

        return {
            "message": "Produit approvisionné avec succès",
            "produit": produit
        }, 200

    except ValueError:
        return {"error": "La quantité doit être un entier valide"}, 400