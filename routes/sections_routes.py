# routes/sections.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from models.user_model import UserModel
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
    Récupérer une section spécifique par son ID
    ---
    tags:
      - Sections
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: section_id
        type: string
        required: true
        description: ID de la section à récupérer
        example: "507f1f77bcf86cd799439011"
    responses:
      200:
        description: Section récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section récupérée avec succès"
            data:
              type: object
              properties:
                _id:
                  type: string
                  example: "507f1f77bcf86cd799439011"
                church_id:
                  type: string
                  example: "507f1f77bcf86cd799439012"
                title:
                  type: string
                  example: "Nouveau Converti"
                description:
                  type: string
                  example: "Section pour les nouveaux convertis"
                order:
                  type: integer
                  example: 1
                is_sequential:
                  type: boolean
                  example: true
                icon:
                  type: string
                  example: "beginner.png"
                is_public:
                  type: boolean
                  example: false
                is_template:
                  type: boolean
                  example: false
                source_section_id:
                  type: string
                  example: null
                stats:
                  type: object
                  properties:
                    total_chapters:
                      type: integer
                      example: 5
                    total_quiz:
                      type: integer
                      example: 15
                    avg_completion_rate:
                      type: number
                      example: 75.5
                created_by:
                  type: string
                  example: "507f1f77bcf86cd799439013"
                created_at:
                  type: string
                  format: date-time
                  example: "2025-01-15T10:30:00Z"
                updated_at:
                  type: string
                  format: date-time
                  example: "2025-01-15T10:30:00Z"
      404:
        description: Section ou utilisateur non trouvé
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section non trouvée"
      403:
        description: Accès non autorisé à cette section
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Accès non autorisé"
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Erreur serveur : détails de l'erreur"
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
    Mettre à jour une section existante
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
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: section_id
        type: string
        required: true
        description: ID de la section à mettre à jour
        example: "507f1f77bcf86cd799439011"
      - in: formData
        name: title
        type: string
        required: false
        description: Nouveau titre de la section
        example: "Disciple Avancé"
      - in: formData
        name: description
        type: string
        required: false
        description: Nouvelle description de la section
        example: "Formation approfondie pour disciples avancés"
      - in: formData
        name: order
        type: integer
        required: false
        description: Nouvel ordre d'affichage
        example: 2
      - in: formData
        name: is_sequential
        type: boolean
        required: false
        description: Modifier le type de section (ordonnée ou parallèle)
        example: false
      - in: formData
        name: icon
        type: file
        required: false
        description: Nouvelle icône de la section (format image)
    responses:
      200:
        description: Section mise à jour avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section mise à jour avec succès"
            modified_count:
              type: integer
              example: 1
      400:
        description: Données de mise à jour invalides
        schema:
          type: object
          properties:
            errors:
              type: object
              example: {"title": ["Le titre doit contenir au moins 3 caractères"]}
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis ou section d'une autre église)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Accès non autorisé"
      404:
        description: Section ou utilisateur non trouvé
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section non trouvée"
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Erreur serveur : détails de l'erreur"
    """
    try:
        data = request.form.to_dict()
        icon_file = request.files.get("icon")
        
        # Valider
        errors = UpdateSectionSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        current_user_id = get_jwt_identity()
        user = UserModel.find_one({"_id": ObjectId(current_user_id)})
        
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
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: section_id
        type: string
        required: true
        description: ID de la section à supprimer
        example: "507f1f77bcf86cd799439011"
    responses:
      200:
        description: Section supprimée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section supprimée avec succès"
            deleted_count:
              type: integer
              example: 1
      400:
        description: Impossible de supprimer (chapitres associés)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Impossible de supprimer cette section. Elle contient 5 chapitre(s)."
            chapters_count:
              type: integer
              example: 5
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis ou section d'une autre église)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Accès non autorisé"
      404:
        description: Section ou utilisateur non trouvé
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section non trouvée"
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Erreur serveur : détails de l'erreur"
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
    Récupérer le catalogue des sections publiques partagées
    ---
    tags:
      - Sections
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Numéro de la page à récupérer
        example: 1
      - in: query
        name: per_page
        type: integer
        required: false
        default: 20
        description: Nombre de sections par page
        example: 20
    responses:
      200:
        description: Catalogue récupéré avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Catalogue récupéré avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "507f1f77bcf86cd799439011"
                  church_id:
                    type: string
                    example: "507f1f77bcf86cd799439012"
                  title:
                    type: string
                    example: "Formation Baptême"
                  description:
                    type: string
                    example: "Préparation complète au baptême d'eau"
                  order:
                    type: integer
                    example: 1
                  is_sequential:
                    type: boolean
                    example: true
                  icon:
                    type: string
                    example: "baptism.png"
                  is_public:
                    type: boolean
                    example: true
                  is_template:
                    type: boolean
                    example: false
                  stats:
                    type: object
                    properties:
                      total_chapters:
                        type: integer
                        example: 8
                      total_quiz:
                        type: integer
                        example: 24
                      avg_completion_rate:
                        type: number
                        example: 82.5
                  created_at:
                    type: string
                    format: date-time
                    example: "2025-01-15T10:30:00Z"
            pagination:
              type: object
              properties:
                page:
                  type: integer
                  example: 1
                per_page:
                  type: integer
                  example: 20
                total:
                  type: integer
                  example: 45
                pages:
                  type: integer
                  example: 3
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Erreur serveur : détails de l'erreur"
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
    Publier une section dans le catalogue partagé
    ---
    tags:
      - Sections
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: section_id
        type: string
        required: true
        description: ID de la section à publier dans le catalogue
        example: "507f1f77bcf86cd799439011"
    responses:
      200:
        description: Section publiée dans le catalogue avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section publiée dans le catalogue avec succès"
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis ou section d'une autre église)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Accès non autorisé"
      404:
        description: Section ou utilisateur non trouvé
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section non trouvée"
      500:
        description: Erreur serveur ou erreur lors de la publication
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Erreur serveur : détails de l'erreur"
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
    Retirer une section du catalogue partagé
    ---
    tags:
      - Sections
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: section_id
        type: string
        required: true
        description: ID de la section à retirer du catalogue
        example: "507f1f77bcf86cd799439011"
    responses:
      200:
        description: Section retirée du catalogue avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section retirée du catalogue avec succès"
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis ou section d'une autre église)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Accès non autorisé"
      404:
        description: Section ou utilisateur non trouvé
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section non trouvée"
      500:
        description: Erreur serveur ou erreur lors du retrait
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Erreur serveur : détails de l'erreur"
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
    Cloner une section publique du catalogue vers son église
    ---
    tags:
      - Sections
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: section_id
        type: string
        required: true
        description: ID de la section publique à cloner depuis le catalogue
        example: "507f1f77bcf86cd799439011"
    responses:
      201:
        description: Section clonée avec succès dans votre église
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section clonée avec succès dans votre église"
            section_id:
              type: string
              example: "507f1f77bcf86cd799439099"
              description: ID de la nouvelle section clonée
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Section non disponible dans le catalogue (non publique ou non template)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Cette section n'est pas disponible dans le catalogue"
      404:
        description: Section source ou utilisateur non trouvé
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section non trouvée"
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Erreur serveur : détails de l'erreur"
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