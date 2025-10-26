# routes/sections.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from schemas.section_schema import CreateSectionSchema, UpdateSectionSchema
from services.section_service import (
    create_section_service,
    get_all_sections_service,
    get_section_by_id_service,
    update_section_service,
    delete_section_service,
    get_catalog_service,
    publish_section_service,
    unpublish_section_service,
    clone_section_service,
    get_sections_with_creator_info
)
from utils.decorators import admin_required

sections_bp = Blueprint("sections", __name__, url_prefix="/api/sections")


@sections_bp.route("/create", methods=["POST"])
@jwt_required()
@admin_required
def create():
    """
    Créer une nouvelle section
    ---
    tags:
      - Sections
    consumes:
      - multipart/form-data
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        example: "Bearer votre.jwt.token"
      - in: formData
        name: title
        type: string
        required: true
        example: "Nouveau Converti"
      - in: formData
        name: description
        type: string
        required: false
        example: "Section pour les nouveaux convertis"
      - in: formData
        name: order
        type: integer
        required: false
        example: 1
      - in: formData
        name: is_sequential
        type: boolean
        required: false
        example: true
      - in: formData
        name: icon
        type: file
        required: false
        description: Icône de la section
    responses:
      201:
        description: Section créée avec succès
      400:
        description: Données invalides
      401:
        description: Non autorisé
    """
    try:
        data = request.form.to_dict()
        icon_file = request.files.get("icon")
        
        # Récupérer l'utilisateur courant
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Ajouter church_id et created_by
        data["church_id"] = str(user["church_id"])
        data["created_by"] = current_user_id
        
        # Convertir is_sequential en boolean
        if "is_sequential" in data:
            data["is_sequential"] = data["is_sequential"].lower() in ["true", "1", "yes"]
        
        # Valider les données
        errors = CreateSectionSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        # Créer la section
        result, status = create_section_service(data, icon_file)
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@sections_bp.route("/list", methods=["GET"])
@jwt_required()
def list_sections():
    """
    Récupérer toutes les sections de l'église
    ---
    tags:
      - Sections
    parameters:
      - in: header
        name: Authorization
        required: true
      - in: query
        name: is_sequential
        type: boolean
        required: false
    responses:
      200:
        description: Liste des sections
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Filtrer par type si spécifié
        is_sequential = None
        if request.args.get("is_sequential"):
            is_sequential = request.args.get("is_sequential").lower() in ["true", "1"]
        
        sections = get_all_sections_service(str(user["church_id"]), is_sequential)
        
        return jsonify({
            "message": "Sections récupérées avec succès",
            "data": sections,
            "total": len(sections)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@sections_bp.route("/<section_id>", methods=["GET"])
@jwt_required()
def get_section(section_id):
    """
    Récupérer une section spécifique
    ---
    tags:
      - Sections
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        section = get_section_by_id_service(section_id)
        
        if not section:
            return jsonify({"message": "Section non trouvée"}), 404
        
        # Vérifier l'accès
        if section["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        return jsonify({
            "message": "Section récupérée avec succès",
            "data": section
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@sections_bp.route("/<section_id>/update", methods=["PUT"])
@jwt_required()
@admin_required
def update_section(section_id):
    """
    Mettre à jour une section
    ---
    tags:
      - Sections
    """
    try:
        data = request.form.to_dict()
        icon_file = request.files.get("icon")
        
        # Valider
        errors = UpdateSectionSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        section = get_section_by_id_service(section_id)
        
        if not section:
            return jsonify({"message": "Section non trouvée"}), 404
        
        if section["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        # Convertir is_sequential si présent
        if "is_sequential" in data:
            data["is_sequential"] = data["is_sequential"].lower() in ["true", "1", "yes"]
        
        result = update_section_service(section_id, data, icon_file)
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@sections_bp.route("/<section_id>/delete", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_section(section_id):
    """
    Supprimer une section
    ---
    tags:
      - Sections
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        section = get_section_by_id_service(section_id)
        
        if not section:
            return jsonify({"message": "Section non trouvée"}), 404
        
        if section["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        result, status = delete_section_service(section_id)
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@sections_bp.route("/catalog", methods=["GET"])
@jwt_required()
def get_catalog():
    """
    Récupérer le catalogue des sections publiques
    ---
    tags:
      - Sections
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        
        result = get_catalog_service(page, per_page)
        
        return jsonify({
            "message": "Catalogue récupéré avec succès",
            "data": result["sections"],
            "pagination": result["pagination"]
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@sections_bp.route("/<section_id>/publish", methods=["POST"])
@jwt_required()
@admin_required
def publish_section(section_id):
    """
    Publier une section dans le catalogue
    ---
    tags:
      - Sections
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        section = get_section_by_id_service(section_id)
        
        if not section:
            return jsonify({"message": "Section non trouvée"}), 404
        
        if section["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        result, status = publish_section_service(section_id)
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@sections_bp.route("/<section_id>/unpublish", methods=["POST"])
@jwt_required()
@admin_required
def unpublish_section(section_id):
    """
    Retirer une section du catalogue
    ---
    tags:
      - Sections
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        section = get_section_by_id_service(section_id)
        
        if not section:
            return jsonify({"message": "Section non trouvée"}), 404
        
        if section["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        result, status = unpublish_section_service(section_id)
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@sections_bp.route("/<section_id>/clone", methods=["POST"])
@jwt_required()
@admin_required
def clone_section(section_id):
    """
    Cloner une section du catalogue vers son église
    ---
    tags:
      - Sections
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = clone_section_service(
            section_id, 
            str(user["church_id"]), 
            current_user_id
        )
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500