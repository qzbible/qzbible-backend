# routes/chapters.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from schemas.chapter_schema import CreateChapterSchema, UpdateChapterSchema
from services.chapter_service import (
    create_chapter_service,
    get_all_chapters_service,
    get_chapter_by_id_service,
    update_chapter_service,
    delete_chapter_service,
    get_chapters_with_creator_info,
    clone_chapter_service
)
from utils.decorators import admin_required
import json

chapters_bp = Blueprint("chapters", __name__, url_prefix="/api/chapters")


@chapters_bp.route("/create", methods=["POST"])
@jwt_required()
@admin_required
def create():
    """
    Créer un nouveau chapitre
    ---
    tags:
      - Chapters
    consumes:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: body
        name: body
        required: true
        description: Données du chapitre à créer
        schema:
          type: object
          required:
            - section_id
            - title
          properties:
            section_id:
              type: string
              example: "507f1f77bcf86cd799439011"
              description: ID de la section parente
            title:
              type: string
              example: "La Foi"
              description: Titre du chapitre
            description:
              type: string
              example: "Introduction à la foi chrétienne"
              description: Description du chapitre
            order:
              type: integer
              example: 1
              description: Ordre d'affichage (auto-calculé si non fourni)
            content:
              type: object
              properties:
                introduction:
                  type: string
                  example: "Dans ce chapitre, nous allons explorer..."
                resources:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                        enum: [video, pdf, audio, link, image]
                        example: "video"
                      url:
                        type: string
                        example: "https://youtube.com/watch?v=..."
                      title:
                        type: string
                        example: "Introduction à la foi"
            unlock_requirements:
              type: object
              properties:
                previous_chapter_id:
                  type: string
                  example: "507f1f77bcf86cd799439010"
                  description: ID du chapitre précédent (null pour le premier)
                min_score:
                  type: integer
                  example: 70
                  description: Score minimum requis (0-100)
                completion_required:
                  type: boolean
                  example: true
                  description: Tous les quiz doivent être complétés
    responses:
      201:
        description: Chapitre créé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Chapitre créé avec succès"
            chapter_id:
              type: string
              example: "507f1f77bcf86cd799439020"
      400:
        description: Données invalides
        schema:
          type: object
          properties:
            errors:
              type: object
              example: {"title": ["Le titre est requis"]}
      404:
        description: Section non trouvée
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section non trouvée"
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis)
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Récupérer l'utilisateur courant
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Ajouter church_id et created_by
        data["church_id"] = str(user["church_id"])
        data["created_by"] = current_user_id
        
        # Valider les données
        errors = CreateChapterSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        # Créer le chapitre
        result, status = create_chapter_service(data)
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@chapters_bp.route("/section/<section_id>", methods=["GET"])
@jwt_required()
def list_by_section(section_id):
    """
    Récupérer tous les chapitres d'une section
    ---
    tags:
      - Chapters
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
        description: ID de la section
        example: "507f1f77bcf86cd799439011"
    responses:
      200:
        description: Liste des chapitres récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Chapitres récupérés avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "507f1f77bcf86cd799439020"
                  section_id:
                    type: string
                    example: "507f1f77bcf86cd799439011"
                  title:
                    type: string
                    example: "La Foi"
                  description:
                    type: string
                    example: "Introduction à la foi chrétienne"
                  order:
                    type: integer
                    example: 1
                  content:
                    type: object
                  unlock_requirements:
                    type: object
                  created_at:
                    type: string
                    format: date-time
            total:
              type: integer
              example: 5
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Section non trouvée
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Vérifier que la section appartient à l'église
        from models.section_model import SectionModel
        section = SectionModel.get_section_by_id(section_id)
        
        if not section:
            return jsonify({"message": "Section non trouvée"}), 404
        
        if section["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        chapters = get_all_chapters_service(section_id)
        
        return jsonify({
            "message": "Chapitres récupérés avec succès",
            "data": chapters,
            "total": len(chapters)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@chapters_bp.route("/<chapter_id>", methods=["GET"])
@jwt_required()
def get_chapter(chapter_id):
    """
    Récupérer un chapitre spécifique par son ID
    ---
    tags:
      - Chapters
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: chapter_id
        type: string
        required: true
        description: ID du chapitre à récupérer
        example: "507f1f77bcf86cd799439020"
    responses:
      200:
        description: Chapitre récupéré avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Chapitre récupéré avec succès"
            data:
              type: object
              properties:
                _id:
                  type: string
                  example: "507f1f77bcf86cd799439020"
                section_id:
                  type: string
                  example: "507f1f77bcf86cd799439011"
                church_id:
                  type: string
                  example: "507f1f77bcf86cd799439012"
                title:
                  type: string
                  example: "La Foi"
                description:
                  type: string
                  example: "Introduction à la foi chrétienne"
                order:
                  type: integer
                  example: 1
                content:
                  type: object
                  properties:
                    introduction:
                      type: string
                      example: "Dans ce chapitre..."
                    resources:
                      type: array
                      items:
                        type: object
                unlock_requirements:
                  type: object
                  properties:
                    previous_chapter_id:
                      type: string
                      example: null
                    min_score:
                      type: integer
                      example: 70
                    completion_required:
                      type: boolean
                      example: true
                is_public:
                  type: boolean
                  example: false
                created_by:
                  type: string
                  example: "507f1f77bcf86cd799439013"
                created_at:
                  type: string
                  format: date-time
                updated_at:
                  type: string
                  format: date-time
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès non autorisé à ce chapitre
      404:
        description: Chapitre ou utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        chapter = get_chapter_by_id_service(chapter_id)
        
        if not chapter:
            return jsonify({"message": "Chapitre non trouvé"}), 404
        
        # Vérifier l'accès
        if chapter["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        return jsonify({
            "message": "Chapitre récupéré avec succès",
            "data": chapter
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@chapters_bp.route("/<chapter_id>/update", methods=["PUT"])
@jwt_required()
@admin_required
def update_chapter(chapter_id):
    """
    Mettre à jour un chapitre existant
    ---
    tags:
      - Chapters
    consumes:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: chapter_id
        type: string
        required: true
        description: ID du chapitre à mettre à jour
        example: "507f1f77bcf86cd799439020"
      - in: body
        name: body
        required: true
        description: Données à mettre à jour
        schema:
          type: object
          properties:
            title:
              type: string
              example: "La Foi - Niveau Avancé"
            description:
              type: string
              example: "Approfondissement de la foi"
            order:
              type: integer
              example: 2
            content:
              type: object
              properties:
                introduction:
                  type: string
                resources:
                  type: array
                  items:
                    type: object
            unlock_requirements:
              type: object
              properties:
                previous_chapter_id:
                  type: string
                min_score:
                  type: integer
                completion_required:
                  type: boolean
    responses:
      200:
        description: Chapitre mis à jour avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Chapitre mis à jour avec succès"
            modified_count:
              type: integer
              example: 1
      400:
        description: Données de mise à jour invalides
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis ou chapitre d'une autre église)
      404:
        description: Chapitre ou utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Valider
        errors = UpdateChapterSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        chapter = get_chapter_by_id_service(chapter_id)
        
        if not chapter:
            return jsonify({"message": "Chapitre non trouvé"}), 404
        
        if chapter["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        result = update_chapter_service(chapter_id, data)
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@chapters_bp.route("/<chapter_id>/delete", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_chapter(chapter_id):
    """
    Supprimer un chapitre
    ---
    tags:
      - Chapters
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: chapter_id
        type: string
        required: true
        description: ID du chapitre à supprimer
        example: "507f1f77bcf86cd799439020"
    responses:
      200:
        description: Chapitre supprimé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Chapitre supprimé avec succès"
            deleted_count:
              type: integer
              example: 1
      400:
        description: Impossible de supprimer (quiz associés)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Impossible de supprimer ce chapitre. Il contient 3 quiz."
            quiz_count:
              type: integer
              example: 3
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis ou chapitre d'une autre église)
      404:
        description: Chapitre ou utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        chapter = get_chapter_by_id_service(chapter_id)
        
        if not chapter:
            return jsonify({"message": "Chapitre non trouvé"}), 404
        
        if chapter["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        result, status = delete_chapter_service(chapter_id)
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@chapters_bp.route("/<chapter_id>/clone", methods=["POST"])
@jwt_required()
@admin_required
def clone_chapter(chapter_id):
    """
    Cloner un chapitre vers une autre section
    ---
    tags:
      - Chapters
    consumes:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: chapter_id
        type: string
        required: true
        description: ID du chapitre à cloner
        example: "507f1f77bcf86cd799439020"
      - in: body
        name: body
        required: true
        description: Section de destination
        schema:
          type: object
          required:
            - target_section_id
          properties:
            target_section_id:
              type: string
              example: "507f1f77bcf86cd799439099"
              description: ID de la section de destination
    responses:
      201:
        description: Chapitre cloné avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Chapitre cloné avec succès"
            chapter_id:
              type: string
              example: "507f1f77bcf86cd799439088"
      400:
        description: Données invalides
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé
      404:
        description: Chapitre ou section non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        if not data.get("target_section_id"):
            return jsonify({"message": "target_section_id est requis"}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Vérifier que la section cible existe et appartient à l'église
        from models.section_model import SectionModel
        target_section = SectionModel.get_section_by_id(data["target_section_id"])
        
        if not target_section:
            return jsonify({"message": "Section de destination non trouvée"}), 404
        
        if target_section["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé à la section de destination"}), 403
        
        result, status = clone_chapter_service(
            chapter_id,
            data["target_section_id"],
            str(user["church_id"]),
            current_user_id
        )
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500