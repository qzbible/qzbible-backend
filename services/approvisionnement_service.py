from datetime import datetime
from schemas.approvisionnement_schema import ApprovisionnementSchema
from models.approvisionnement_model import ApprovisionnementModel
from models.stock_livreur_model import StockLivreurModel
from models.produit_model import ProduitModel
from marshmallow import ValidationError
from utils.error_handler import verifier_produits_approvisionnement_valide
from models.user_model import UserModel 
from bson import ObjectId


def approvisionner_livreur(data):
    try:
        validated_data = ApprovisionnementSchema().load(data)
    except ValidationError as err:
        return {"error": err.messages}, 400

    # Doit être fait uniquement si la validation a réussi
    produits = validated_data["produits"]

    # Validation personnalisée
    is_valid, error = verifier_produits_approvisionnement_valide(produits)
    if not is_valid:
        return {"error": error}, 400

    # 1. Enregistrer l'approvisionnement
    appro_id = ApprovisionnementModel.enregistrer_approvisionnement(validated_data)

    # 2. Mettre à jour le stock du livreur
    livreur_id = validated_data["livreur_id"]
    StockLivreurModel.ajouter_stock(livreur_id, produits)

    # 3. Décrémenter le stock du magasin
    acteur = {"admin_id": validated_data["admin_id"], "livreur_id": livreur_id}
    for produit in produits:
        ProduitModel.decrement_stock(
            produit_id=produit["produit_id"],
            quantite=produit["quantite"],
            acteur=acteur,
            type_mouvement="approvisionnement_livreur"
        )

    return {"message": "Approvisionnement réussi", "approvisionnement_id": appro_id}, 201


def serialize_approvisionnement(approvisionnement_data):
    # Récupération des informations du livreur
    livreur_data = UserModel.find_by_id(approvisionnement_data['livreur_id'])
    
    if livreur_data:
        livreur_data.pop("_id", None)  # suppression de l'id du livreur
        prenom_livreur = livreur_data.get("name", "") 
        nom_livreur =  livreur_data.get("first_name", "")
    else:
        prenom_livreur = ""
        nom_livreur = ""
    
    id = str(approvisionnement_data["_id"])
    produits = approvisionnement_data.get("produits", [])
    # Calcul du montant total des produits
    # Note: Le montant total n'est pas calculé ici car il n'est pas stocké dans le modèle
    for produit in produits:
        produit_id = produit.get("produit_id")
        if produit_id:
            produit_data = ProduitModel.get_by_id(produit_id)
            if produit_data:
                produit["nom"] = produit_data.get("nom", "Nom inconnu")
                produit["prix"] = produit_data.get("prix", 0)
            else:
                produit["nom"] = "Nom inconnu"
                produit["prix"] = 0
        else:
            produit["nom"] = "ID inconnu"
            produit["prix"] = 0
    montant_total = sum([produit.get("prix", 0) * produit.get("quantite", 0) for produit in produits])
    quantite_total = sum([produit.get("quantite", 0) for produit in produits])
    
    return {
        "id": id,
        "first_name": prenom_livreur,
        "last_name": nom_livreur,
        "montant": montant_total,
        "quantite": quantite_total,
        "produits" : produits,
        "created_at": (
            approvisionnement_data["created_at"].isoformat()
            if isinstance(approvisionnement_data["created_at"], datetime)
            else str(approvisionnement_data["created_at"])
        ),
    }

# Récupérer tous les approvisionnement effectué par un manager
def get_approvisionner_service(admin_or_manager_id):
    """
    retourne tous les approvisionnements initiés par un manager ou administrateur
    """
    approvisionnement_data = ApprovisionnementModel.get_all_by_manager(admin_or_manager_id)
    
    # Trie des approvionnements par date de création
    approvisionnement_data_tries = sorted(
        approvisionnement_data,
        key=lambda l:l.get("created_at", datetime.min), 
        reverse=True
    )
    approvisionnement_nettoyees = [serialize_approvisionnement(a) for a in approvisionnement_data_tries]
    

    return approvisionnement_nettoyees, 200
    
    
"""    
# Supprimer un approvisionnement
def delete_approvisionnement_service(approvisionnement_id):
 
    try:
        # Étape 1 : Récupérer l'approvisionnement
        approvisionnement = ApprovisionnementModel.get_by_id(approvisionnement_id)
        if not approvisionnement:
            return {"message": "Approvisionnement introuvable"}, 404

        produits = approvisionnement.get("produits", [])
        livreur_id = approvisionnement.get("livreur_id")

        if not produits or not livreur_id:
            return {"message": "Approvisionnement invalide : données incomplètes"}, 400

        # ✅ Étape 2 : Ajuster les stocks
        for produit in produits:
            try:
                produit_id = produit.get("produit_id")
                quantite = produit.get("quantite")

                if not produit_id or quantite is None:
                    print(f"⛔ Produit mal structuré : {produit}")
                    continue

                produit_id = ObjectId(produit_id)

                # Vérifier que le produit existe dans la base principale
                if not ProduitModel.get_by_id(str(produit_id)):
                    print(f"⛔ Produit {produit_id} introuvable dans la base principale")
                    continue

                # ✅ Retirer du stock du livreur → avec sécurité
                try:
                    StockLivreurModel.retirer_du_stock(str(livreur_id), str(produit_id), quantite)
                except Exception as retrait_err:
                    print(f"⚠️ Impossible de retirer produit {produit_id} du stock du livreur {livreur_id} : {retrait_err}")
                    continue  # on saute ce produit


                # ✅ Tracer le retour
                ProduitModel.increment_stock(
                    produit_id=str(produit_id),
                    quantite=quantite,
                    acteur={"livreur_id": str(livreur_id)},
                    type_mouvement="annulation_approvisionnement",
                )

            except Exception as e:
                print(f"⛔ Erreur inattendue pour produit {produit.get('produit_id')} : {e}")
                continue

        # ✅ Étape 3 : Supprimer l'approvisionnement
        ApprovisionnementModel.collection.delete_one({"_id": ObjectId(approvisionnement["_id"])})

        return {"message": "Approvisionnement supprimé avec succès"}, 200

    except Exception as e:
        import traceback
        traceback.print_exc()  # ← affiche la trace complète dans la console
        return {"message": f"Erreur lors de la suppression : {str(e)}"}, 500
"""
def delete_approvisionnement_service(approvisionnement_id):
    """
    Supprime un approvisionnement :
    - Réintègre les produits restants dans le stock principal
    - Réduit le stock du livreur selon ce qui est encore disponible
    - Supprime l'enregistrement d'approvisionnement
    - Ajoute un mouvement de stock de type 'annulation_approvisionnement'
    """
    try:
        approvisionnement = ApprovisionnementModel.get_by_id(approvisionnement_id)
        if not approvisionnement:
            return {"message": "Approvisionnement introuvable"}, 404

        produits = approvisionnement.get("produits", [])
        livreur_id = approvisionnement.get("livreur_id")

        if not produits or not livreur_id:
            return {"message": "Approvisionnement invalide : données incomplètes"}, 400

        for produit in produits:
            try:
                produit_id = produit.get("produit_id")
                quantite_appro = produit.get("quantite")

                if not produit_id or quantite_appro is None:
                    print(f"⛔ Produit mal structuré : {produit}")
                    continue

                produit_id_obj = ObjectId(produit_id)

                if not ProduitModel.get_by_id(str(produit_id_obj)):
                    print(f"⛔ Produit {produit_id} introuvable dans la base principale")
                    continue

                # Vérifier stock réel chez le livreur
                filtre = {
                    "livreur_id": ObjectId(livreur_id),
                    "produit_id": produit_id_obj
                }
                stock_livreur = StockLivreurModel.collection.find_one(filtre)
                quantite_en_stock = stock_livreur["quantite"] if stock_livreur else 0

                if quantite_en_stock <= 0:
                    print(f"⚠️ Aucune quantité disponible à rapatrier pour produit {produit_id}")
                    continue

                # Calcul de la quantité à récupérer
                quantite_a_retirer = min(quantite_en_stock, quantite_appro)

                # Retirer du stock livreur
                try:
                    StockLivreurModel.retirer_du_stock(str(livreur_id), str(produit_id_obj), quantite_a_retirer)
                except Exception as retrait_err:
                    print(f"⚠️ Erreur de retrait stock livreur : {retrait_err}")
                    continue

                # Rapatrier dans le stock principal
                type_mvt = "annulation_approvisionnement" if quantite_a_retirer == quantite_appro else "annulation_approvisionnement_partielle"
                ProduitModel.increment_stock(
                    produit_id=str(produit_id_obj),
                    quantite=quantite_a_retirer,
                    acteur={"livreur_id": str(livreur_id)},
                    type_mouvement=type_mvt,
                )

            except Exception as e:
                print(f"⛔ Erreur inattendue pour produit {produit.get('produit_id')} : {e}")
                continue

        # Supprimer l'approvisionnement même partiellement traité
        ApprovisionnementModel.collection.delete_one({"_id": ObjectId(approvisionnement["_id"])})

        return {"message": "Approvisionnement supprimé (restant récupéré si possible)"}, 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"message": f"Erreur lors de la suppression : {str(e)}"}, 500





# détails d'un approvisionnement
def get_approvisionnement_details_service(approvisionnement_id):
    """
    Récupère les détails d'un approvisionnement spécifique.
    """
    approvisionnement = ApprovisionnementModel.get_by_id(approvisionnement_id)
    
    if not approvisionnement:
        return {"message": "Approvisionnement introuvable"}, 404
    
    # Sérialisation des données
    approvisionnement_details = serialize_approvisionnement(approvisionnement)
    #print("approvionnement : ", approvisionnement_details)
    
    return approvisionnement_details, 200