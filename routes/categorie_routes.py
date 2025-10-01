# routes/categorie_routes.py

from flask import Blueprint, request, jsonify
from utils.inject_magasin_id import inject_magasin_id
from utils.decorators import role_required  # Import the missing decorator
from flask_jwt_extended import jwt_required  # Import jwt_required
from schemas.categorie_schema import CreateCategorieSchema, UpdateCategorieSchema
from services.categorie_service import (
    create_categorie_service,
    get_categories_by_magasin_service,
    update_categorie_service,
    delete_categorie_service,
    get_categorie_details_service
)

categorie_bp = Blueprint("categorie", __name__, url_prefix="/categorie")


#Cree une nouvelle catégorie dans un magasin


@categorie_bp.route("/create", methods=["POST"])
@jwt_required()
@role_required("admin", "manager", "livreur")
def create_categorie():
    """
    Création d’une catégorie
    ---
    tags:
      - Catégories
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - nom
            - magasin_id
          properties:
            nom:
              type: string
              example: "Catégorie Exemple"
            description:
              type: string
              example: "Description de la catégorie"
            magasin_id:
              type: string
              example: "605c72ef1532072e7c32ed47"
    responses:
      201:
        description: Catégorie créée avec succès
      400:
        description: Erreur dans les données envoyées
    """
    data = request.get_json()
    data = inject_magasin_id(data)
    errors = CreateCategorieSchema().validate(data)
    if errors:
        return jsonify({"errors": errors}), 400
    return create_categorie_service(data)


# voir toute les catégories de produit d’un magasin

@categorie_bp.route("/", methods=["GET"])
@jwt_required()
@role_required("admin", "manager", "livreur")
def get_categories_by_magasin():
    """
    Récupération des catégories d’un magasin
    ---
    tags:
      - Catégories
    parameters:
      - in: path
        name: magasin_id
        required: true
        type: string
        description: ID du magasin
        example: "605c72ef1532072e7c32ed47"
    responses:
      200:
        description: Liste des catégories du magasin
        schema:
          type: array
          items:
            type: object
            properties:
              _id:
                type: string
                example: "605c72ef1532072e7c32ed48"
              nom:
                type: string
                example: "Catégorie Exemple"
              description:
                type: string
                example: "Description de la catégorie"
              magasin_id:
                type: string
                example: "605c72ef1532072e7c32ed47"
    responses:
      404:
        description: Magasin non trouvé
    """
    data = {}
    data = inject_magasin_id(data)
    magasin_id = data.get("magasin_id")
    categories = get_categories_by_magasin_service(magasin_id)
    for cat in categories:
        cat["_id"] = str(cat["_id"])
        cat["magasin_id"] = str(cat["magasin_id"])
    return jsonify(categories), 200


# Mettre à jour une catégorie

@categorie_bp.route("/<categorie_id>", methods=["PUT"])
@jwt_required()
@role_required("admin", "manager", "livreur")
def update_categorie(categorie_id):
    """
    Mise à jour d’une catégorie
    ---
    tags:
      - Catégories
    parameters:
      - in: path
        name: categorie_id
        required: true
        type: string
        description: ID de la catégorie à mettre à jour
        example: "605c72ef1532072e7c32ed48"
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - nom
          properties:
            nom:
              type: string
              example: "Catégorie Exemple Modifiée"
            description:
              type: string
              example: "Nouvelle description"
    responses:
      200:
        description: Catégorie mise à jour avec succès
      400:
        description: Erreur dans les données envoyées
    """
    data = request.get_json()
    errors = UpdateCategorieSchema().validate(data)
    if errors:
        return jsonify({"errors": errors}), 400

    update_categorie_service(categorie_id, data)
    return jsonify({"message": "Catégorie mise à jour"}), 200


@categorie_bp.route("/<categorie_id>", methods=["DELETE"])
@jwt_required()
@role_required("admin", "manager", "livreur")
def delete_categorie(categorie_id):
    """
    Suppression d’une catégorie
    ---
    tags:
      - Catégories
    parameters:
      - in: path
        name: categorie_id
        required: true
        type: string
        description: ID de la catégorie à supprimer
        example: "605c72ef1532072e7c32ed48"
    responses:
      200:
        description: Catégorie supprimée avec succès
      404:
        description: Catégorie non trouvée
    """
    delete_categorie_service(categorie_id)
    return jsonify({"message": "Catégorie supprimée"}), 200


# Détails d'un catégorie
@categorie_bp.route("/<categorie_id>", methods=["GET"])
@jwt_required()
@role_required("admin", "manager", "livreur", "staff")
def get_categorie_details(categorie_id):
    """
    Récupération des détails d’une catégorie
    ---
    tags:
      - Catégories
    parameters:
      - in: path
        name: categorie_id
        required: true
        type: string
        description: ID de la catégorie à récupérer
        example: "605c72ef1532072e7c32ed48"
    responses:
      200:
        description: Détails de la catégorie récupérés avec succès
      404:
        description: Catégorie non trouvée
    """
    categorie = get_categorie_details_service(categorie_id)
    if not categorie:
        return jsonify({"message": "Catégorie non trouvée"}), 404

    categorie["_id"] = str(categorie["_id"])
    categorie["magasin_id"] = str(categorie["magasin_id"])
    return jsonify(categorie), 200