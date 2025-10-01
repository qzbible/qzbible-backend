# Fonction de gestion des erreurs
from flask import jsonify
import os
from bson import ObjectId
from extensions import mongo
from models.produit_model import ProduitModel


def handle_error(message, status_code):
    return jsonify({"error": message}), status_code


def delete_file(file_path):
    """
    Supprime un fichier s'il existe.

    :param file_path: Chemin du fichier à supprimer.
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            print(f"Fichier supprimé : {file_path}")
        else:
            print(f"Fichier non trouvé ou déjà supprimé : {file_path}")
    except Exception as e:
        print(f"Erreur lors de la suppression du fichier {file_path} : {e}")


# Vérifie si un produit et une catégorie appartiennent au même magasin

def verifie_produit_et_categorie_meme_magasin(produit_id, categorie_id):
    """
    Vérifie que le produit et la catégorie appartiennent au même magasin.

    :param produit_id: ID du produit (str ou ObjectId)
    :param categorie_id: ID de la catégorie (str ou ObjectId)
    :return: True s'ils sont dans le même magasin, False sinon
    """
    produit = mongo.db.produits.find_one({"_id": ObjectId(produit_id)})
    categorie = mongo.db.categories.find_one({"_id": ObjectId(categorie_id)})

    if not produit or not categorie:
        return False

    return produit["magasin_id"] == categorie["magasin_id"]


# utils/validation.py



def verifier_produits_approvisionnement_valide(produits: list):
    """
    Vérifie que :
    - Tous les produits viennent du même magasin.
    - Aucun produit ne dépasse le stock disponible.
    """
    if not produits:
        return False, "Aucun produit fourni"

    magasin_reference = None

    for produit in produits:
        produit_obj = ProduitModel.get_by_id(produit["produit_id"])
        if not produit_obj:
            return False, f"Produit {produit['produit_id']} introuvable"

        # Vérifier stock suffisant
        if produit["quantite"] > produit_obj["quantite"]:
            return False, f"Stock insuffisant pour le produit '{produit_obj['nom']}' (disponible: {produit_obj['quantite']}, demandé: {produit['quantite']})"

        # Vérifier cohérence magasin
        if magasin_reference is None:
            magasin_reference = produit_obj["magasin_id"]
        elif str(produit_obj["magasin_id"]) != str(magasin_reference):
            return False, f"Tous les produits doivent appartenir au même magasin. Conflit détecté avec le produit '{produit_obj['nom']}'"

    return True, None
