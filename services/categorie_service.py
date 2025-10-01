# services/categorie_services.py

from models.categorie_model import CategorieModel
from flask import jsonify

def create_categorie_service(data):
    result =  CategorieModel.create_categorie(data)
    return result
def get_categorie_details_service(categorie_id):
    categorie = CategorieModel.get_categorie_by_id(categorie_id)
    if not categorie:
        return jsonify({"message": "Catégorie non trouvée"}), 404
    return categorie

def get_categories_by_magasin_service(magasin_id):
    return CategorieModel.get_all_by_magasin(magasin_id)

def update_categorie_service(categorie_id, data):
    return CategorieModel.update_categorie(categorie_id, data)

def delete_categorie_service(categorie_id):
    return CategorieModel.delete_categorie(categorie_id)
