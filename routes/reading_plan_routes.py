# routes/simple_reading_plan.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId

from schemas.reading_plan_schema import (
    CreateSimplePlanSchema,
    SubscribeSimplePlanSchema,
    MarkDayCompletedSchema
)
from services.reading_plan_service import (
    create_simple_plan_service,
    get_simple_plans_service,
    get_simple_plan_detail_service,
    subscribe_to_simple_plan_service,
    get_user_simple_plans_service,
    mark_day_completed_service,
    get_current_reading_service,
    search_simple_plans_service
)

simple_plans_bp = Blueprint("simple_plans", __name__, url_prefix="/api/simple-plans")

@simple_plans_bp.route("", methods=["GET"])
@jwt_required()
def get_simple_plans():
    """
    Récupérer les plans de lecture simples
    ---
    tags:
      - Simple Reading Plans
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: query
        name: book_focus
        type: string
        required: false
        description: Filtrer par livre(s) (séparés par des virgules)
        example: "Psaumes,Proverbes"
      - in: query
        name: duration_months
        type: integer
        required: false
        description: Filtrer par durée en mois
        example: 2
      - in: query
        name: search
        type: string
        required: false
        description: Terme de recherche
        example: "méditation"
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Numéro de page
        example: 1
      - in: query
        name: per_page
        type: integer
        required: false
        default: 20
        description: Nombre d'éléments par page
        example: 20
    responses:
      200:
        description: Plans récupérés avec succès
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
                total:
                  type: integer
                page:
                  type: integer
                per_page:
                  type: integer
                total_pages:
                  type: integer
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        # Préparer les filtres
        filters = {}
        
        if request.args.get("book_focus"):
            filters["book_focus"] = request.args.get("book_focus").split(",")
        
        if request.args.get("duration_months"):
            try:
                filters["duration_months"] = int(request.args.get("duration_months"))
            except:
                pass
        
        if request.args.get("search"):
            filters["search"] = request.args.get("search")
        
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        
        result = get_simple_plans_service(filters if filters else None, page, per_page)
        
        return jsonify({
            "message": "Plans de lecture récupérés avec succès",
            **result
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@simple_plans_bp.route("/<plan_id>", methods=["GET"])
@jwt_required()
def get_simple_plan(plan_id):
    """
    Récupérer les détails d'un plan simple
    ---
    tags:
      - Simple Reading Plans
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
        description: ID du plan
        example: "507f1f77bcf86cd799439060"
    responses:
      200:
        description: Détails du plan récupérés avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                title:
                  type: string
                  example: "Psaumes et Proverbes"
                subtitle:
                  type: string
                  example: "Méditation quotidienne"
                description:
                  type: string
                duration:
                  type: object
                daily_reading:
                  type: object
                notifications:
                  type: object
                auto_save:
                  type: object
                schedule_preview:
                  type: array
                meta:
                  type: object
      404:
        description: Plan non trouvé
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        result = get_simple_plan_detail_service(plan_id)
        
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@simple_plans_bp.route("/create", methods=["POST"])
@jwt_required()
def create_simple_plan():
    """
    Créer un plan de lecture simple
    ---
    tags:
      - Simple Reading Plans
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - title
              - subtitle
              - description
              - duration_months
              - daily_chapters
              - book_focus
              - reading_schedule
            properties:
              title:
                type: string
                example: "Psaumes et Proverbes"
              subtitle:
                type: string
                example: "Méditation quotidienne"
              description:
                type: string
                example: "Car l'Éternel donne la sagesse..."
              duration_months:
                type: integer
                example: 2
              daily_chapters:
                type: integer
                example: 2
              book_focus:
                type: array
                items:
                  type: string
                example: ["Psaumes", "Proverbes"]
              reading_schedule:
                type: array
                items:
                  type: object
                  properties:
                    day:
                      type: integer
                    label:
                      type: string
                    passages:
                      type: array
                      items:
                        type: string
                    estimated_time:
                      type: integer
              emoji:
                type: string
                example: "💛"
              color:
                type: string
                example: "#FFA726"
    responses:
      201:
        description: Plan créé avec succès
      400:
        description: Données invalides
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Validation des données
        errors = CreateSimplePlanSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        result, status = create_simple_plan_service(data)
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@simple_plans_bp.route("/<plan_id>/start", methods=["POST"])
@jwt_required()
def start_simple_plan(plan_id):
    """
    Commencer un plan de lecture simple
    ---
    tags:
      - Simple Reading Plans
    parameters:
      - in: path
        name: plan_id
        required: true
        schema:
          type: string
    requestBody:
      required: false
      content:
        application/json:
          schema:
            type: object
            properties:
              reminder_time:
                type: string
                example: "07:00"
              reminder_enabled:
                type: boolean
                example: true
    responses:
      201:
        description: Plan commencé avec succès
      400:
        description: Déjà inscrit ou données invalides
      404:
        description: Plan non trouvé
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # Validation des données
        errors = SubscribeSimplePlanSchema().validate({**data, "plan_id": plan_id})
        if errors:
            return jsonify({"errors": errors}), 400
        
        result, status = subscribe_to_simple_plan_service(plan_id, current_user_id, data)
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@simple_plans_bp.route("/my-plans", methods=["GET"])
@jwt_required()
def get_my_simple_plans():
    """
    Récupérer mes plans de lecture simples
    ---
    tags:
      - Simple Reading Plans
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
      - in: query
        name: status
        schema:
          type: string
          enum: [active, completed, paused]
        description: Filtrer par statut
    responses:
      200:
        description: Plans récupérés avec succès
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        status = request.args.get("status")
        
        plans = get_user_simple_plans_service(current_user_id, status)
        
        return jsonify({
            "message": "Vos plans récupérés avec succès",
            "data": plans,
            "total": len(plans)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@simple_plans_bp.route("/user-plan/<user_plan_id>/complete-day", methods=["POST"])
@jwt_required()
def complete_day(user_plan_id):
    """
    Marquer un jour comme complété
    ---
    tags:
      - Simple Reading Plans
    parameters:
      - in: path
        name: user_plan_id
        required: true
        schema:
          type: string
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - day
            properties:
              day:
                type: integer
                example: 1
    responses:
      200:
        description: Jour marqué comme complété
      400:
        description: Données invalides
      404:
        description: Plan non trouvé
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Validation des données
        errors = MarkDayCompletedSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        result, status = mark_day_completed_service(user_plan_id, data["day"])
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@simple_plans_bp.route("/user-plan/<user_plan_id>/current", methods=["GET"])
@jwt_required()
def get_current_reading(user_plan_id):
    """
    Récupérer la lecture actuelle
    ---
    tags:
      - Simple Reading Plans
    parameters:
      - in: path
        name: user_plan_id
        required: true
        schema:
          type: string
    responses:
      200:
        description: Lecture actuelle récupérée
      404:
        description: Plan non trouvé
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        result = get_current_reading_service(user_plan_id)
        
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        
        return jsonify({
            "message": "Lecture actuelle récupérée avec succès",
            "data": result
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@simple_plans_bp.route("/search", methods=["GET"])
@jwt_required()
def search_simple_plans():
    """
    Rechercher dans les plans simples
    ---
    tags:
      - Simple Reading Plans
    parameters:
      - in: query
        name: q
        required: true
        schema:
          type: string
        description: Terme de recherche
    responses:
      200:
        description: Résultats de recherche
      400:
        description: Terme de recherche manquant
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        search_term = request.args.get("q")
        
        if not search_term:
            return jsonify({"message": "Terme de recherche requis (paramètre 'q')"}), 400
        
        plans = search_simple_plans_service(search_term)
        
        return jsonify({
            "message": "Résultats de recherche récupérés avec succès",
            "data": plans,
            "total": len(plans)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

def register_simple_plans_blueprints(app):
    """Enregistrer le blueprint"""
    app.register_blueprint(simple_plans_bp)