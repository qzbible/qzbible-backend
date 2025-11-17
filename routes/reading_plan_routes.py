# routes/reading_plan.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
import os
from werkzeug.utils import secure_filename
from datetime import datetime

from schemas.reading_plan_schema import *
from services.reading_plan_service import *
from utils.decorators import admin_required

reading_plan_bp = Blueprint("reading_plan", __name__, url_prefix="/api/reading-plans")
 

@reading_plan_bp.route("", methods=["GET"])
@jwt_required()
def get_reading_plans():
    """
    Récupérer les plans de lecture disponibles
    ---
    tags:
      - Reading Plans
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: query
        name: category
        schema:
          type: string
          enum: [bible, books, study, mixed]
        description: Filtrer par catégorie
        example: "bible"
      - in: query
        name: difficulty
        schema:
          type: string
          enum: [beginner, intermediate, advanced]
        description: Filtrer par niveau de difficulté
        example: "beginner"
      - in: query
        name: creator_type
        schema:
          type: string
          enum: [admin, pastor, user]
        description: Filtrer par type de créateur
        example: "admin"
      - in: query
        name: duration_range
        schema:
          type: string
          pattern: '^\\d+-\\d+$'
        description: Filtrer par durée en jours (format min-max)
        example: "7-30"
      - in: query
        name: tags
        schema:
          type: string
        description: Filtrer par tags (séparés par des virgules)
        example: "baptême,nouveau-converti"
      - in: query
        name: search
        schema:
          type: string
          maxLength: 100
        description: Recherche textuelle
        example: "formation"
      - in: query
        name: sort_by
        schema:
          type: string
          enum: [created_at, popular, rating]
          default: created_at
        description: Critère de tri
        example: "popular"
      - in: query
        name: page
        schema:
          type: integer
          minimum: 1
          default: 1
        description: Numéro de page
        example: 1
      - in: query
        name: per_page
        schema:
          type: integer
          minimum: 1
          maximum: 100
          default: 20
        description: Nombre d'éléments par page
        example: 20
    responses:
      200:
        description: Plans de lecture récupérés avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Plans de lecture récupérés avec succès"
                data:
                  type: array
                  items:
                    type: object
                    properties:
                      _id:
                        type: string
                        example: "507f1f77bcf86cd799439060"
                      title:
                        type: string
                        example: "Formation Nouveau Converti"
                      description:
                        type: string
                        example: "Un plan complet pour les nouveaux convertis"
                      category:
                        type: string
                        enum: [bible, books, study, mixed]
                        example: "study"
                      creator:
                        type: object
                        properties:
                          user_id:
                            type: string
                          creator_type:
                            type: string
                            enum: [admin, pastor, user]
                          church_id:
                            type: string
                          church_name:
                            type: string
                      visibility:
                        type: string
                        enum: [public, private, church_only]
                      duration_days:
                        type: integer
                        example: 30
                      estimated_daily_time:
                        type: integer
                        example: 15
                      difficulty_level:
                        type: string
                        enum: [beginner, intermediate, advanced]
                      tags:
                        type: array
                        items:
                          type: string
                        example: ["baptême", "nouveau-converti"]
                      stats:
                        type: object
                        properties:
                          subscribers:
                            type: integer
                            example: 45
                          completions:
                            type: integer
                            example: 23
                          average_rating:
                            type: number
                            example: 4.5
                      created_at:
                        type: string
                        format: date-time
                total:
                  type: integer
                  example: 150
                page:
                  type: integer
                  example: 1
                per_page:
                  type: integer
                  example: 20
                total_pages:
                  type: integer
                  example: 8
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        # Préparer les filtres
        filters = {}
        
        if request.args.get("category"):
            filters["category"] = request.args.get("category")
        if request.args.get("difficulty"):
            filters["difficulty"] = request.args.get("difficulty")
        if request.args.get("creator_type"):
            filters["creator_type"] = request.args.get("creator_type")
        if request.args.get("duration_range"):
            filters["duration_range"] = request.args.get("duration_range")
        if request.args.get("tags"):
            filters["tags"] = request.args.get("tags").split(",")
        if request.args.get("search"):
            filters["search"] = request.args.get("search")
        if request.args.get("sort_by"):
            filters["sort_by"] = request.args.get("sort_by")
        
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        
        result = get_reading_plans_service(filters if filters else None, page, per_page)
        
        return jsonify({
            "message": "Plans de lecture récupérés avec succès",
            **result
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@reading_plan_bp.route("/<plan_id>", methods=["GET"])
@jwt_required()
def get_reading_plan(plan_id):
    """
    Récupérer les détails d'un plan de lecture
    ---
    tags:
      - Reading Plans
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: plan_id
        required: true
        schema:
          type: string
        description: ID du plan de lecture
        example: "507f1f77bcf86cd799439060"
    responses:
      200:
        description: Détails du plan récupérés avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Détails du plan récupérés avec succès"
                data:
                  type: object
                  properties:
                    _id:
                      type: string
                    title:
                      type: string
                    description:
                      type: string
                    category:
                      type: string
                      enum: [bible, books, study, mixed]
                    creator:
                      type: object
                      properties:
                        user_id:
                          type: string
                        creator_type:
                          type: string
                        church_name:
                          type: string
                    content_items:
                      type: array
                      items:
                        type: object
                        properties:
                          item_id:
                            type: string
                          day:
                            type: integer
                          order:
                            type: integer
                          content_type:
                            type: string
                          content_ref:
                            type: object
                            properties:
                              type:
                                type: string
                              resource_id:
                                type: string
                              specific_ref:
                                type: string
                              display_ref:
                                type: string
                          title:
                            type: string
                          estimated_time:
                            type: integer
                          is_optional:
                            type: boolean
                    duration_days:
                      type: integer
                    estimated_daily_time:
                      type: integer
                    stats:
                      type: object
      404:
        description: Plan non trouvé
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        result = get_reading_plan_detail_service(plan_id)
        
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        
        return jsonify({
            "message": "Détails du plan récupérés avec succès",
            "data": result
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@reading_plan_bp.route("/create", methods=["POST"])
@jwt_required()
def create_reading_plan():
    """
    Créer un nouveau plan de lecture
    ---
    tags:
      - Reading Plans
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - title
              - category
              - duration_days
              - estimated_daily_time
              - content_items
            properties:
              title:
                type: string
                minLength: 3
                maxLength: 200
                example: "Étude de l'Évangile de Jean"
                description: "Titre du plan de lecture"
              description:
                type: string
                maxLength: 1000
                example: "Une étude approfondie de l'Évangile de Jean"
                description: "Description optionnelle"
              category:
                type: string
                enum: [bible, books, study, mixed]
                example: "bible"
                description: "Catégorie du plan"
              visibility:
                type: string
                enum: [public, private, church_only]
                default: private
                example: "public"
              duration_days:
                type: integer
                minimum: 1
                maximum: 365
                example: 30
                description: "Durée du plan en jours"
              estimated_daily_time:
                type: integer
                minimum: 1
                example: 15
                description: "Temps quotidien estimé en minutes"
              difficulty_level:
                type: string
                enum: [beginner, intermediate, advanced]
                default: intermediate
                example: "beginner"
              tags:
                type: array
                items:
                  type: string
                maxItems: 10
                example: ["evangile", "jean", "nouveau-testament"]
                description: "Tags pour faciliter la recherche"
              content_items:
                type: array
                minItems: 1
                items:
                  type: object
                  required:
                    - item_id
                    - day
                    - order
                    - content_type
                    - content_ref
                    - title
                    - estimated_time
                  properties:
                    item_id:
                      type: string
                      example: "day_1_item_1"
                    day:
                      type: integer
                      minimum: 1
                      example: 1
                    order:
                      type: integer
                      minimum: 1
                      example: 1
                    content_type:
                      type: string
                      example: "bible_passage"
                    content_ref:
                      type: object
                      required:
                        - type
                        - resource_id
                        - specific_ref
                        - display_ref
                      properties:
                        type:
                          type: string
                          enum: [bible_passage, document_section, video, audio, article]
                        resource_id:
                          type: string
                        specific_ref:
                          type: string
                        page_ref:
                          type: string
                        display_ref:
                          type: string
                    title:
                      type: string
                      example: "Jean 1:1-14 - Le Verbe fait chair"
                    estimated_time:
                      type: integer
                      minimum: 1
                      example: 10
                    is_optional:
                      type: boolean
                      default: false
                    notes:
                      type: string
              quiz_integration:
                type: object
                properties:
                  has_quizzes:
                    type: boolean
                    default: false
    responses:
      201:
        description: Plan créé avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Plan de lecture créé avec succès"
                plan_id:
                  type: string
                  example: "507f1f77bcf86cd799439060"
      400:
        description: Données invalides
        content:
          application/json:
            schema:
              type: object
              properties:
                errors:
                  type: object
                  description: "Erreurs de validation Marshmallow"
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Validation des données
        errors = CreateReadingPlanSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = create_reading_plan_service(
            data,
            current_user_id,
            str(user.get("church_id")) if user.get("church_id") else None
        )
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@reading_plan_bp.route("/quick-create", methods=["POST"])
@jwt_required()
def quick_create_reading_plan():
    """
    Création rapide de plan avec templates
    ---
    tags:
      - Reading Plans
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - template_type
              - source
            properties:
              template_type:
                type: string
                enum: [document_study, bible_study, mixed_study]
                example: "document_study"
                description: "Type de template à utiliser"
              source:
                type: object
                required:
                  - type
                  - document_id
                  - strategy
                  - daily_target
                properties:
                  type:
                    type: string
                    example: "document"
                  document_id:
                    type: string
                    example: "507f1f77bcf86cd799439011"
                    description: "ID du document source"
                  strategy:
                    type: string
                    enum: [time_based, page_based, chapter_based]
                    example: "page_based"
                    description: "Stratégie de division du contenu"
                  daily_target:
                    type: integer
                    minimum: 1
                    example: 5
                    description: "Objectif quotidien (pages ou minutes selon strategy)"
                  include_bible:
                    type: boolean
                    default: false
                    description: "Inclure des passages bibliques liés"
              plan_info:
                type: object
                properties:
                  title:
                    type: string
                    example: "Mon plan personnalisé"
                  visibility:
                    type: string
                    enum: [public, private, church_only]
                    default: private
              preferences:
                type: object
                properties:
                  start_date:
                    type: string
                    format: date
                    example: "2024-01-15"
                  reminder_enabled:
                    type: boolean
                    default: true
                  reminder_time:
                    type: string
                    pattern: '^([01]\d|2[0-3]):([0-5]\d)$'
                    example: "07:00"
                  weekend_reading:
                    type: boolean
                    default: true
    responses:
      201:
        description: Plan créé et souscription effectuée avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Plan créé et souscription effectuée avec succès"
                data:
                  type: object
                  properties:
                    plan_id:
                      type: string
                    user_plan_id:
                      type: string
                    generated_schedule:
                      type: array
                      description: "Aperçu des 5 premiers jours"
                      items:
                        type: object
                    summary:
                      type: object
                      properties:
                        total_duration:
                          type: integer
                        daily_average_time:
                          type: integer
                        completion_date:
                          type: string
                          format: date-time
      400:
        description: Données invalides
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Utilisateur ou document non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Validation des données
        errors = QuickCreatePlanSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = quick_create_plan_service(
            data,
            current_user_id,
            str(user.get("church_id")) if user.get("church_id") else None
        )
        
        return jsonify({
            "message": "Plan créé et souscription effectuée avec succès",
            "data": result
        }), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@reading_plan_bp.route("/subscribe", methods=["POST"])
@jwt_required()
def subscribe_to_reading_plan():
    """
    S'inscrire à un plan de lecture
    ---
    tags:
      - Reading Plans
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - plan_id
            properties:
              plan_id:
                type: string
                example: "507f1f77bcf86cd799439060"
                description: "ID du plan de lecture"
              customizations:
                type: object
                properties:
                  daily_reminder_time:
                    type: string
                    pattern: '^([01]\d|2[0-3]):([0-5]\d)$'
                    default: "07:00"
                    example: "07:00"
                    description: "Heure de rappel quotidien (HH:MM)"
                  reminder_days:
                    type: array
                    items:
                      type: string
                      enum: [monday, tuesday, wednesday, thursday, friday, saturday, sunday]
                    default: ["monday", "tuesday", "wednesday", "thursday", "friday"]
                    example: ["monday", "tuesday", "wednesday", "thursday", "friday"]
                    description: "Jours de rappel"
                  pace:
                    type: string
                    enum: [slow, normal, fast]
                    default: normal
                    example: "normal"
                    description: "Rythme de lecture"
                  bible_version:
                    type: string
                    default: "louis_segond"
                    example: "louis_segond"
                    description: "Version biblique préférée"
                  catch_up_mode:
                    type: string
                    enum: [extend_duration, compress_readings, skip_missed]
                    default: "extend_duration"
                    description: "Mode de rattrapage par défaut"
    responses:
      201:
        description: Inscription au plan réussie
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Inscription au plan réussie"
                user_plan_id:
                  type: string
                  example: "507f1f77bcf86cd799439061"
      400:
        description: Données invalides ou utilisateur déjà inscrit
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Plan ou utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Validation des données
        errors = SubscribeToPlanSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = subscribe_to_plan_service(
            data["plan_id"],
            current_user_id,
            str(user.get("church_id")) if user.get("church_id") else None,
            data["customizations"]
        )
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@reading_plan_bp.route("/user/<user_id>", methods=["GET"])
@jwt_required()
def get_user_reading_plans(user_id):
    """
    Récupérer les plans d'un utilisateur
    ---
    tags:
      - Reading Plans
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: user_id
        required: true
        schema:
          type: string
        description: ID de l'utilisateur
        example: "507f1f77bcf86cd799439050"
      - in: query
        name: status
        schema:
          type: string
          enum: [active, paused, completed, abandoned]
        description: Filtrer par statut
        example: "active"
    responses:
      200:
        description: Plans utilisateur récupérés avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Plans utilisateur récupérés avec succès"
                data:
                  type: array
                  items:
                    type: object
                    properties:
                      _id:
                        type: string
                      user_id:
                        type: string
                      plan_id:
                        type: string
                      status:
                        type: string
                        enum: [active, paused, completed, abandoned]
                      progress:
                        type: object
                        properties:
                          completion_percentage:
                            type: number
                            example: 65.5
                          current_day:
                            type: integer
                            example: 15
                          started_at:
                            type: string
                            format: date-time
                          estimated_completion_date:
                            type: string
                            format: date-time
                      plan_details:
                        type: object
                        properties:
                          title:
                            type: string
                          description:
                            type: string
                          category:
                            type: string
                      customizations:
                        type: object
                      created_at:
                        type: string
                        format: date-time
                total:
                  type: integer
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès non autorisé (peut seulement voir ses propres plans)
      500:
        description: Erreur serveur
    """
    try:
        current_user = get_jwt_identity()
        
        # Vérifier que l'utilisateur demande ses propres plans
        if str(current_user) != user_id:
            return jsonify({"message": "Accès non autorisé"}), 403
        
        status_filter = request.args.get("status")
        plans = get_user_plans_service(user_id, status_filter)
        
        return jsonify({
            "message": "Plans utilisateur récupérés avec succès",
            "data": plans,
            "total": len(plans)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@reading_plan_bp.route("/user-plan/<user_plan_id>/progress", methods=["POST"])
@jwt_required()
def mark_reading_progress(user_plan_id):
    """
    Marquer la progression de lecture
    ---
    tags:
      - Reading Plans
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: user_plan_id
        required: true
        schema:
          type: string
        description: ID du plan utilisateur
        example: "507f1f77bcf86cd799439061"
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - item_id
            properties:
              item_id:
                type: string
                example: "day_1_item_1"
                description: "ID de l'élément complété"
              completed:
                type: boolean
                default: true
                example: true
              time_spent:
                type: integer
                minimum: 0
                example: 8
                description: "Temps passé en minutes"
              notes:
                type: string
                maxLength: 500
                example: "Très inspirant!"
                description: "Notes personnelles"
              rating:
                type: integer
                minimum: 1
                maximum: 5
                example: 5
                description: "Note de 1 à 5"
    responses:
      200:
        description: Progression mise à jour
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Progression mise à jour"
                completion_percentage:
                  type: number
                  example: 65.5
                current_day:
                  type: integer
                  example: 15
                completed:
                  type: boolean
                  example: false
                  description: "true si le plan entier est terminé"
      400:
        description: Données invalides
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Plan utilisateur ou élément non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Validation des données
        errors = MarkProgressSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        result, status = mark_reading_progress_service(
            user_plan_id,
            data["item_id"],
            {
                "completed": data.get("completed", True),
                "time_spent": data.get("time_spent", 0),
                "notes": data.get("notes", ""),
                "rating": data.get("rating")
            }
        )
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@reading_plan_bp.route("/user-plan/<user_plan_id>/catch-up-options", methods=["GET"])
@jwt_required()
def get_catch_up_options(user_plan_id):
    """
    Récupérer les options de rattrapage
    ---
    tags:
      - Reading Plans
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: user_plan_id
        required: true
        schema:
          type: string
        description: ID du plan utilisateur
        example: "507f1f77bcf86cd799439061"
    responses:
      200:
        description: Options de rattrapage récupérées avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Options de rattrapage récupérées avec succès"
                data:
                  type: object
                  properties:
                    days_behind:
                      type: integer
                      example: 5
                      description: "Nombre de jours de retard"
                    options:
                      type: array
                      items:
                        type: object
                        properties:
                          type:
                            type: string
                            enum: [extend_duration, compress_readings, skip_optional]
                          description:
                            type: string
                          additional_days:
                            type: integer
                          new_end_date:
                            type: string
                            format: date-time
                          daily_increase:
                            type: string
                          items_to_skip:
                            type: integer
                          days_saved:
                            type: integer
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Plan utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        options = get_catch_up_options_service(user_plan_id)
        
        return jsonify({
            "message": "Options de rattrapage récupérées avec succès",
            "data": options
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@reading_plan_bp.route("/user-plan/<user_plan_id>/catch-up", methods=["POST"])
@jwt_required()
def apply_catch_up_strategy(user_plan_id):
    """
    Appliquer une stratégie de rattrapage
    ---
    tags:
      - Reading Plans
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: user_plan_id
        required: true
        schema:
          type: string
        description: ID du plan utilisateur
        example: "507f1f77bcf86cd799439061"
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - strategy
            properties:
              strategy:
                type: string
                enum: [extend_duration, compress_readings, skip_optional]
                example: "extend_duration"
                description: "Stratégie de rattrapage à appliquer"
              params:
                type: object
                description: "Paramètres spécifiques à la stratégie"
                properties:
                  additional_days:
                    type: integer
                    example: 5
                    description: "Pour extend_duration: jours supplémentaires"
                  factor:
                    type: number
                    example: 1.2
                    description: "Pour compress_readings: facteur de compression"
    responses:
      200:
        description: Stratégie de rattrapage appliquée
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Stratégie de rattrapage appliquée"
                strategy_applied:
                  type: string
                  example: "extend_duration"
      400:
        description: Données invalides
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Plan utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Validation des données
        errors = CatchUpStrategySchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        result, status = apply_catch_up_strategy_service(
            user_plan_id,
            data["strategy"],
            data.get("params", {})
        )
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

 