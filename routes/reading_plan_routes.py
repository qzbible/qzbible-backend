# routes/simple_reading_plan.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId

from models.reading_plan_model import UserSimplePlanModel
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

reading_plan_bp = Blueprint("simple_plans", __name__, url_prefix="/api/simple-plans")

@reading_plan_bp.route("", methods=["GET"])
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
        schema:
          type: string
        required: false
        description: Filtrer par livre(s) (séparés par des virgules)
        example: "Psaumes,Proverbes"
      - in: query
        name: duration_months
        schema:
          type: integer
        required: false
        description: Filtrer par durée en mois
        example: 2
      - in: query
        name: search
        schema:
          type: string
        required: false
        description: Terme de recherche
        example: "méditation"
      - in: query
        name: page
        schema:
          type: integer
          default: 1
        required: false
        description: Numéro de page
        example: 1
      - in: query
        name: per_page
        schema:
          type: integer
          default: 20
        required: false
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
                    properties:
                      _id:
                        type: string
                        example: "507f1f77bcf86cd799439060"
                      title:
                        type: string
                        example: "Psaumes et Proverbes"
                      subtitle:
                        type: string
                        example: "Méditation quotidienne"
                      description:
                        type: string
                      settings:
                        type: object
                        properties:
                          duration_months:
                            type: integer
                          daily_chapters:
                            type: integer
                      meta:
                        type: object
                        properties:
                          emoji:
                            type: string
                          color:
                            type: string
                      stats:
                        type: object
                        properties:
                          subscribers:
                            type: integer
                          completions:
                            type: integer
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

@reading_plan_bp.route("/<plan_id>", methods=["GET"])
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
                  example: "Car l'Éternel donne la sagesse; De sa bouche sortent la connaissance et l'intelligence - Proverbes 2:6"
                duration:
                  type: object
                  properties:
                    months:
                      type: integer
                      example: 2
                    label:
                      type: string
                      example: "2 mois"
                daily_reading:
                  type: object
                  properties:
                    chapters:
                      type: integer
                      example: 2
                    label:
                      type: string
                      example: "2 chapitres par jour"
                notifications:
                  type: object
                  properties:
                    available:
                      type: boolean
                      example: true
                    label:
                      type: string
                      example: "Notifications quotidiennes disponibles"
                auto_save:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                      example: true
                    label:
                      type: string
                      example: "Progression automatiquement sauvegardée"
                schedule_preview:
                  type: array
                  items:
                    type: object
                    properties:
                      day:
                        type: integer
                        example: 1
                      label:
                        type: string
                        example: "Jour 1"
                      passages:
                        type: array
                        items:
                          type: string
                        example: ["Genèse 1-3"]
                      estimated_time:
                        type: integer
                        example: 15
                meta:
                  type: object
                  properties:
                    emoji:
                      type: string
                      example: "💛"
                    color:
                      type: string
                      example: "#FFA726"
                stats:
                  type: object
                  properties:
                    subscribers:
                      type: integer
                      example: 245
                    completions:
                      type: integer
                      example: 89
                    avg_rating:
                      type: number
                      example: 4.5
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

@reading_plan_bp.route("/create", methods=["POST"])
@jwt_required()
def create_simple_plan():
    """
    Créer un plan de lecture simple avec configuration des notifications
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
      - in: body
        name: body
        required: true
        description: Données du plan de lecture avec paramètres de notification
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
            has_notifications:
              type: boolean
              example: true
            auto_save_progress:
              type: boolean
              example: true
            is_template:
              type: boolean
              example: false
            notification_settings:
              type: object
              properties:
                enabled:
                  type: boolean
                  example: true
                  description: "Activer les notifications"
                default_time:
                  type: string
                  example: "07:00"
                  description: "Heure par défaut"
                frequency:
                  type: string
                  enum: [daily, weekly, monthly]
                  example: "daily"
                  description: "Fréquence des notifications"
                recurrence_pattern:
                  type: object
                  properties:
                    type:
                      type: string
                      enum: [daily, weekly, monthly, yearly]
                      example: "daily"
                    interval:
                      type: integer
                      example: 1
                      description: "Intervalle (tous les X jours/semaines/mois)"
                    days_of_week:
                      type: array
                      items:
                        type: integer
                        minimum: 0
                        maximum: 6
                      example: [1, 2, 3, 4, 5]
                      description: "Jours de la semaine (0=dim, 1=lun, ...)"
                    day_of_month:
                      type: integer
                      minimum: 1
                      maximum: 31
                      example: 18
                      description: "Jour du mois (pour récurrence mensuelle)"
                    end_condition:
                      type: object
                      properties:
                        type:
                          type: string
                          enum: [never, date, count]
                          example: "never"
                        end_date:
                          type: string
                          format: date
                          example: "2025-12-31"
                        occurrences:
                          type: integer
                          example: 30
                reminder_types:
                  type: array
                  items:
                    type: string
                    enum: [notification, email, sms]
                  example: ["notification"]
                advance_reminders:
                  type: array
                  items:
                    type: object
                    properties:
                      minutes:
                        type: integer
                        example: 15
                      hours:
                        type: integer
                        example: 1
                  example: [{"minutes": 15}]
                custom_message:
                  type: string
                  example: "Temps de lecture biblique !"
                  description: "Message personnalisé"
    responses:
      201:
        description: Plan créé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Plan de lecture créé avec succès"
            plan_id:
              type: string
              example: "507f1f77bcf86cd799439060"
            auto_subscribed:
              type: boolean
              example: true
            user_plan_id:
              type: string
              example: "507f1f77bcf86cd799439061"
      400:
        description: Données invalides
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()
        
        # Validation des données
        errors = CreateSimplePlanSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        # Créer le plan en spécifiant le créateur
        result, status = create_simple_plan_service(data, current_user_id)
        
        if status == 201:
            # Automatiquement inscrire le créateur au plan
            plan_id = result["plan_id"]
            subscription_result, _ = subscribe_to_simple_plan_service(
                plan_id, 
                current_user_id, 
                {"reminder_time": "07:00", "reminder_enabled": True}
            )
            
            # Ajouter l'info d'inscription dans la réponse
            result["auto_subscribed"] = True
            result["user_plan_id"] = subscription_result.get("user_plan_id")
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@reading_plan_bp.route("/<plan_id>/start", methods=["POST"])
@jwt_required()
def start_simple_plan(plan_id):
    """
    Commencer un plan avec préférences de notification personnalisées
    ---
    tags:
      - Simple Reading Plans
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
      - in: path
        name: plan_id
        required: true
        schema:
          type: string
      - in: body
        name: body
        required: false
        description: Préférences de notification personnalisées
        schema:
          type: object
          properties:
            reminder_time:
              type: string
              example: "07:00"
            reminder_enabled:
              type: boolean
              example: true
            notification_preferences:
              type: object
              properties:
                enabled:
                  type: boolean
                  example: true
                reminder_time:
                  type: string
                  example: "08:00"
                  description: "Heure de rappel personnalisée"
                frequency:
                  type: string
                  enum: [daily, weekly, custom]
                  example: "daily"
                days_of_week:
                  type: array
                  items:
                    type: integer
                    minimum: 0
                    maximum: 6
                  example: [1, 2, 3, 4, 5, 6]
                  description: "Jours actifs (lun-sam)"
                recurrence:
                  type: object
                  properties:
                    type:
                      type: string
                      enum: [daily, weekly, monthly]
                      example: "daily"
                    interval:
                      type: integer
                      example: 1
                      description: "Tous les X jours/semaines"
                    custom_pattern:
                      type: string
                      example: "Tous les matins sauf dimanche"
                advance_reminders:
                  type: array
                  items:
                    type: object
                    properties:
                      minutes:
                        type: integer
                      hours:
                        type: integer
                  example: [{"minutes": 15}, {"hours": 1}]
                  description: "Rappels en avance"
                reminder_types:
                  type: array
                  items:
                    type: string
                    enum: [push, email, sms]
                  example: ["push", "email"]
                custom_message:
                  type: string
                  example: "Il est temps de lire la Bible !"
                snooze_options:
                  type: array
                  items:
                    type: integer
                  example: [5, 15, 30]
                  description: "Options de report en minutes"
                quiet_hours:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                      example: true
                    start_time:
                      type: string
                      example: "22:00"
                      description: "Début des heures de silence"
                    end_time:
                      type: string
                      example: "06:00"
                      description: "Fin des heures de silence"
                  description: "Heures de silence (pas de notifications)"
    responses:
      201:
        description: Plan commencé avec succès
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
        
        # ✅ Validation sans plan_id
        errors = SubscribeSimplePlanSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        result, status = subscribe_to_simple_plan_service(plan_id, current_user_id, data)
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@reading_plan_bp.route("/my-plans", methods=["GET"])
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
        description: Token JWT de l'utilisateur
      - in: query
        name: status
        schema:
          type: string
          enum: [active, completed, paused]
        description: Filtrer par statut
      - in: query
        name: type
        schema:
          type: string
          enum: [created, subscribed, all]
          default: all
        description: Type de plans (créés par moi, auxquels je suis inscrit, ou tous)
    responses:
      200:
        description: Plans récupérés avec succès
        schema:
          type: object
          properties:
            message:
              type: string
            data:
              type: array
              items:
                type: object
                properties:
                  plan_details:
                    type: object
                    properties:
                      is_owner:
                        type: boolean
                        description: "true si l'utilisateur a créé ce plan"
            total:
              type: integer
    """
    try:
        current_user_id = get_jwt_identity()
        status = request.args.get("status")
        filter_type = request.args.get("type", "all")  # created, subscribed, all
        
        plans = get_user_simple_plans_service(current_user_id, status, filter_type)
        
        return jsonify({
            "message": "Vos plans récupérés avec succès",
            "data": plans,
            "total": len(plans)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@reading_plan_bp.route("/user-plan/<user_plan_id>/complete-day", methods=["POST"])
@jwt_required()
def complete_day(user_plan_id):
    """
    Marquer un jour comme complété
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
              - day
            properties:
              day:
                type: integer
                example: 1
                description: "Numéro du jour à marquer comme complété"
    responses:
      200:
        description: Jour marqué comme complété
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Jour marqué comme complété"
                current_day:
                  type: integer
                  example: 2
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

@reading_plan_bp.route("/user-plan/<user_plan_id>/current", methods=["GET"])
@jwt_required()
def get_current_reading(user_plan_id):
    """
    Récupérer la lecture actuelle
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
        name: user_plan_id
        required: true
        schema:
          type: string
        description: ID du plan utilisateur
        example: "507f1f77bcf86cd799439061"
    responses:
      200:
        description: Lecture actuelle récupérée
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Lecture actuelle récupérée avec succès"
                data:
                  type: object
                  properties:
                    current_reading:
                      type: object
                      properties:
                        day:
                          type: integer
                          example: 1
                        label:
                          type: string
                          example: "Jour 1"
                        passages:
                          type: array
                          items:
                            type: string
                          example: ["Genèse 1-3"]
                        estimated_time:
                          type: integer
                          example: 15
                    progress:
                      type: object
                      properties:
                        current_day:
                          type: integer
                        completed_days:
                          type: array
                          items:
                            type: integer
                        completion_percentage:
                          type: number
                    plan_title:
                      type: string
                      example: "Psaumes et Proverbes"
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

@reading_plan_bp.route("/search", methods=["GET"])
@jwt_required()
def search_simple_plans():
    """
    Rechercher dans les plans simples
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
        name: q
        required: true
        schema:
          type: string
        description: Terme de recherche
        example: "psaumes"
    responses:
      200:
        description: Résultats de recherche
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Résultats de recherche récupérés avec succès"
                data:
                  type: array
                  items:
                    type: object
                total:
                  type: integer
      400:
        description: Terme de recherche manquant
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Terme de recherche requis (paramètre 'q')"
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

 
@reading_plan_bp.route("/user-plan/<user_plan_id>/notification-settings", methods=["PUT"])
@jwt_required()
def update_notification_settings(user_plan_id):
    """
    Mettre à jour les paramètres de notification d'un plan utilisateur
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
        name: user_plan_id
        required: true
        schema:
          type: string
        description: ID du plan utilisateur
        example: "507f1f77bcf86cd799439061"
      - in: body
        name: body
        required: true
        description: Nouveaux paramètres de notification
        schema:
          type: object
          properties:
            enabled:
              type: boolean
              example: true
              description: "Activer/désactiver les notifications"
            reminder_time:
              type: string
              example: "08:30"
              description: "Nouvelle heure de rappel"
            frequency:
              type: string
              enum: [daily, weekly, custom]
              example: "weekly"
              description: "Fréquence des notifications"
            days_of_week:
              type: array
              items:
                type: integer
                minimum: 0
                maximum: 6
              example: [1, 3, 5]
              description: "Jours spécifiques (lun, mer, ven)"
            recurrence:
              type: object
              properties:
                type:
                  type: string
                  enum: [daily, weekly, monthly]
                  example: "weekly"
                interval:
                  type: integer
                  example: 2
                  description: "Toutes les 2 semaines"
                custom_pattern:
                  type: string
                  example: "Tous les 3 jours"
            advance_reminders:
              type: array
              items:
                type: object
                properties:
                  minutes:
                    type: integer
                    example: 30
                  hours:
                    type: integer
                    example: 2
              example: [{"minutes": 30}, {"hours": 2}]
            reminder_types:
              type: array
              items:
                type: string
                enum: [push, email, sms]
              example: ["push", "email"]
            custom_message:
              type: string
              example: "Moment de méditation biblique !"
              description: "Message personnalisé pour les rappels"
            snooze_options:
              type: array
              items:
                type: integer
              example: [10, 30, 60]
              description: "Options de report (minutes)"
            quiet_hours:
              type: object
              properties:
                enabled:
                  type: boolean
                  example: true
                start_time:
                  type: string
                  example: "21:30"
                end_time:
                  type: string
                  example: "07:00"
              description: "Plage horaire sans notifications"
    responses:
      200:
        description: Paramètres mis à jour avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Paramètres de notification mis à jour"
      404:
        description: Plan utilisateur non trouvé
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        result = UserSimplePlanModel.get_collection().update_one(
            {"_id": ObjectId(user_plan_id)},
            {"$set": {"notification_preferences": data}}
        )
        
        if result.modified_count == 0:
            return jsonify({"message": "Plan non trouvé ou aucune modification"}), 404
        
        return jsonify({"message": "Paramètres de notification mis à jour"}), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur : {str(e)}"}), 500