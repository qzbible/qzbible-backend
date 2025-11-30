# routes/simple_reading_plan.py

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId

from models.reading_plan_model import SimpleReadingPlanModel, UserSimplePlanModel
from schemas.reading_plan_schema import (
    CreateSimplePlanSchema,
    SubscribeSimplePlanSchema,
    MarkDayCompletedSchema
)
from services.reading_plan_service import (
    create_simple_plan_service,
    get_simple_plan_details_service, 
    get_user_simple_plans_service,
    pause_plan_service,
    resume_plan_service
)

reading_plan_bp = Blueprint("simple_plans", __name__, url_prefix="/api/simple-plans")

 
@reading_plan_bp.route("/<plan_id>", methods=["GET"])
@jwt_required()
def get_simple_plan_details(plan_id):
    """
    Récupérer les détails complets d'un plan de lecture
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
      - in: path
        name: plan_id
        required: true
        schema:
          type: string
        description: ID du plan de lecture
      - in: query
        name: include_all_days
        schema:
          type: boolean
          default: false
        description: Inclure tous les jours du plan (sinon seulement les 5 jours pertinents)
    responses:
      200:
        description: Détails du plan récupérés avec succès
        schema:
          type: object
          properties:
            message:
              type: string
            data:
              type: object
              properties:
                _id:
                  type: string
                title:
                  type: string
                description:
                  type: string
                emoji:
                  type: string
                color:
                  type: string
                start_date:
                  type: string
                end_date:
                  type: string
                duration_months:
                  type: integer
                has_notifications:
                  type: boolean
                notification_settings:
                  type: object
                is_owner:
                  type: boolean
                  description: "Si l'utilisateur actuel est le créateur"
                days:
                  type: array
                  description: "Jours du plan (5 pertinents ou tous selon le paramètre)"
                progression:
                  type: object
                  properties:
                    total_days:
                      type: integer
                    elapsed_days:
                      type: integer
                    completion_percentage:
                      type: number
                    status_label:
                      type: string
                    current_day:
                      type: integer
      404:
        description: Plan non trouvé
      403:
        description: Accès non autorisé
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        include_all_days = request.args.get("include_all_days", "false").lower() == "true"
        
        # Récupérer les détails du plan
        plan_details = get_simple_plan_details_service(plan_id, current_user_id, include_all_days)
        
        if not plan_details:
            return jsonify({"message": "Plan non trouvé ou accès non autorisé"}), 404
        
        return jsonify({
            "message": "Détails du plan récupérés avec succès",
            "data": plan_details
        }), 200
        
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
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
            - description
            - duration_months
            - start_date
          properties:
            title:
              type: string
              example: "Psaumes et Proverbes"
              description: "Titre du plan"
            description:
              type: string
              example: "Car l'Éternel donne la sagesse..."
              description: "Description du plan"
            duration_months:
              type: integer
              minimum: 1
              maximum: 12
              example: 2
              description: "Durée en mois"
            start_date:
              type: string
              format: date
              example: "2024-01-15"
              description: "Date de début du plan (YYYY-MM-DD)"
            emoji:
              type: string
              example: "💛"
              description: "Emoji du plan"
            color:
              type: string
              example: "#8C2AE7"
              description: "Couleur en hexadécimal"
            has_notifications:
              type: boolean
              default: true
              example: true
              description: "Activer les notifications"
            auto_save_progress:
              type: boolean
              default: true
              example: true
              description: "Sauvegarde automatique"
            is_template:
              type: boolean
              default: false
              example: false
              description: "Si c'est un template"
            notification_settings:
              type: object
              description: "Configuration des notifications"
              properties:
                enabled:
                  type: boolean
                  default: true
                  example: true
                  description: "Notifications activées"
                default_time:
                  type: string
                  default: "07:00"
                  example: "11:00"
                  description: "Heure par défaut (HH:mm)"
                reminder_types:
                  type: array
                  items:
                    type: string
                    enum: [notification, email, sms]
                  default: ["notification"]
                  example: ["notification"]
                  description: "Types de rappels"
                advance_reminders:
                  type: array
                  items:
                    type: object
                    properties:
                      minutes:
                        type: integer
                        minimum: 1
                        example: 15
                        description: "Minutes avant"
                      hours:
                        type: integer
                        minimum: 1
                        example: 1
                        description: "Heures avant"
                  default: []
                  example: [{"minutes": 15}]
                  description: "Rappels avancés"
                custom_message:
                  type: string
                  example: "Temps de lecture biblique !"
                  description: "Message personnalisé"
                recurrence_pattern:
                  type: object
                  description: "Pattern de récurrence"
                  properties:
                    type:
                      type: string
                      enum: [daily, weekly, monthly, yearly]
                      default: "daily"
                      example: "weekly"
                      description: "Type de récurrence"
                    interval:
                      type: integer
                      minimum: 1
                      default: 1
                      example: 1
                      description: "Intervalle (tous les X jours/semaines/mois)"
                    days_of_week:
                      type: array
                      items:
                        type: integer
                        minimum: 0
                        maximum: 6
                      default: []
                      example: [1, 3, 5]
                      description: "Jours de la semaine (0=dim, 1=lun, ...)"
                    day_of_month:
                      type: integer
                      minimum: 1
                      maximum: 31
                      example: 29
                      description: "Jour du mois (pour récurrence mensuelle)"
                    end_condition:
                      type: object
                      description: "Condition de fin"
                      properties:
                        type:
                          type: string
                          enum: [never, date, count]
                          default: "never"
                          example: "never"
                          description: "Type de condition de fin"
                        end_date:
                          type: string
                          format: date
                          example: "2025-12-31"
                          description: "Date de fin (si type=date)"
                        occurrences:
                          type: integer
                          minimum: 1
                          example: 30
                          description: "Nombre d'occurrences (si type=count)"
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
            start_date:
              type: string
              format: date
              example: "2024-01-15"
              description: "Date de début calculée"
            end_date:
              type: string
              format: date
              example: "2024-03-15"
              description: "Date de fin calculée"
      400:
        description: Données invalides
        schema:
          type: object
          properties:
            errors:
              type: object
              example:
                title: ["Ce champ est requis."]
                start_date: ["Format de date invalide."]
      401:
        description: Token JWT manquant ou invalide
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Token manquant ou invalide"
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
        data = request.get_json()
        current_user_id = get_jwt_identity()
        
        # Validation des données
        errors = CreateSimplePlanSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        # Créer le plan en spécifiant le créateur
        result, status = create_simple_plan_service(data, current_user_id)
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500
@reading_plan_bp.route("/my-plans", methods=["GET"])
@jwt_required()
def get_my_simple_plans():
    """
    Récupérer mes plans créés avec calcul de progression automatique
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
        description: Filtrer par statut (optionnel)
    responses:
      200:
        description: Plans avec progression récupérés
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
                  _id:
                    type: string
                  title:
                    type: string
                  description:
                    type: string
                  emoji:
                    type: string
                  color:
                    type: string
                  start_date:
                    type: string
                  end_date:
                    type: string
                  duration_months:
                    type: integer
                  progression:
                    type: object
                    properties:
                      total_days:
                        type: integer
                        description: "Durée totale en jours"
                      elapsed_days:
                        type: integer
                        description: "Jours écoulés depuis le début"
                      remaining_days:
                        type: integer
                        description: "Jours restants"
                      completion_percentage:
                        type: number
                        description: "Pourcentage d'avancement temporel"
                      current_date:
                        type: string
                        description: "Date du jour"
                      status_label:
                        type: string
                        example: "En cours - Jour 15/60"
                      status_color:
                        type: string
                      is_completed:
                        type: boolean
                      is_started:
                        type: boolean
            total:
              type: integer
    """
    try:
        current_user_id = get_jwt_identity()
        status_filter = request.args.get("status")
        
        plans = get_user_simple_plans_service(current_user_id, status_filter)
        
        return jsonify({
            "message": "Vos plans récupérés avec succès",
            "data": plans,
            "total": len(plans)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500
    
  
@reading_plan_bp.route("/user-plan/<user_plan_id>", methods=["DELETE"])
@jwt_required()
def delete_user_plan(user_plan_id):
    """
    Supprimer définitivement un plan utilisateur
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
        name: user_plan_id
        required: true
        schema:
          type: string
    responses:
      200:
        description: Plan supprimé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Plan supprimé avec succès"
      404:
        description: Plan non trouvé
      401:
        description: Token JWT invalide
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Vérifier que le plan appartient à l'utilisateur
        user_plan = SimpleReadingPlanModel.get_collection().find_one({
            "_id": ObjectId(user_plan_id)
            
        })
        
        if not user_plan:
            return jsonify({"message": "Plan non trouvé ou accès refusé"}), 404
        
        # Supprimer le plan
        result = SimpleReadingPlanModel.get_collection().delete_one({
            "_id": ObjectId(user_plan_id)
        })
        
        if result.deleted_count == 0:
            return jsonify({"message": "Erreur lors de la suppression"}), 500
        
       
        
        return jsonify({
            "message": "Plan supprimé avec succès"
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur : {str(e)}"}), 500
    
  
@reading_plan_bp.route("/<plan_id>/pause", methods=["POST"])
@jwt_required()
def pause_plan(plan_id):
    """
    Mettre un plan en pause
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
        schema:
          type: object
          properties:
            reason:
              type: string
              example: "Voyage de 5 jours"
            pause_date:
              type: string
              format: date
              example: "2025-11-30"
              description: "Date de pause (défaut: aujourd'hui)"
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        result = pause_plan_service(plan_id, current_user_id, data)
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur : {str(e)}"}), 500

@reading_plan_bp.route("/<plan_id>/resume", methods=["POST"])
@jwt_required()
def resume_plan(plan_id):
    """
    Reprendre un plan en pause
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
        schema:
          type: object
          properties:
            resume_date:
              type: string
              format: date
              example: "2025-12-05"
              description: "Date de reprise (défaut: aujourd'hui)"
            adjust_schedule:
              type: boolean
              example: true
              description: "Ajuster les dates futures (défaut: true)"
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        result = resume_plan_service(plan_id, current_user_id, data)
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur : {str(e)}"}), 500