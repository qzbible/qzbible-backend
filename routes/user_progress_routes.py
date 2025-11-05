# routes/user_progress.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from schemas.user_progress_schema import ManualUnlockSchema
from services.user_progress_service import (
    get_user_progress_service,
    get_section_progress_service,
    get_chapter_progress_service,
    manual_unlock_chapter_service,
    get_learners_progress_service,
    get_dashboard_stats_service,
    get_leaderboard_service,
    reset_user_progress_service
)
from utils.decorators import admin_required

user_progress_bp = Blueprint("user_progress", __name__, url_prefix="/api/user-progress")


@user_progress_bp.route("/my-progress", methods=["GET"])
@jwt_required()
def get_my_progress():
    """
    Récupérer ma progression complète
    ---
    tags:
      - User Progress
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
    responses:
      200:
        description: Progression récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Progression récupérée avec succès"
            data:
              type: object
              properties:
                _id:
                  type: string
                user_id:
                  type: string
                church_id:
                  type: string
                sections_progress:
                  type: array
                  description: Progression par section
                  items:
                    type: object
                    properties:
                      section_id:
                        type: string
                      status:
                        type: string
                        enum: [not_started, in_progress, completed]
                      started_at:
                        type: string
                        format: date-time
                      completed_at:
                        type: string
                        format: date-time
                      chapters_progress:
                        type: array
                        items:
                          type: object
                          properties:
                            chapter_id:
                              type: string
                            status:
                              type: string
                            is_unlocked:
                              type: boolean
                            unlocked_at:
                              type: string
                              format: date-time
                            unlocked_by:
                              type: string
                            quizzes_progress:
                              type: array
                            completion_percentage:
                              type: number
                            avg_score:
                              type: number
                      completion_percentage:
                        type: number
                      total_time_spent_seconds:
                        type: integer
                overall_stats:
                  type: object
                  properties:
                    total_quiz_completed:
                      type: integer
                    total_quiz_passed:
                      type: integer
                    avg_score:
                      type: number
                    total_time_spent_seconds:
                      type: integer
                    current_streak_days:
                      type: integer
                    longest_streak_days:
                      type: integer
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        progress = get_user_progress_service(current_user_id, str(user["church_id"]))
        
        return jsonify({
            "message": "Progression récupérée avec succès",
            "data": progress
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@user_progress_bp.route("/section/<section_id>", methods=["GET"])
@jwt_required()
def get_section_progress(section_id):
    """
    Récupérer ma progression pour une section spécifique
    ---
    tags:
      - User Progress
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
        description: Progression de la section récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Progression de la section récupérée avec succès"
            data:
              type: object
              properties:
                section_id:
                  type: string
                status:
                  type: string
                  enum: [not_started, in_progress, completed]
                started_at:
                  type: string
                  format: date-time
                completed_at:
                  type: string
                  format: date-time
                chapters_progress:
                  type: array
                  description: Progression des chapitres
                  items:
                    type: object
                completion_percentage:
                  type: number
                  example: 65.5
                total_time_spent_seconds:
                  type: integer
                  example: 7200
                section_info:
                  type: object
                  description: Informations de la section
                  properties:
                    title:
                      type: string
                      example: "Nouveau Converti"
                    description:
                      type: string
                    is_sequential:
                      type: boolean
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Progression ou section non trouvée
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        section_prog = get_section_progress_service(
            current_user_id, 
            str(user["church_id"]), 
            section_id
        )
        
        return jsonify({
            "message": "Progression de la section récupérée avec succès",
            "data": section_prog
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@user_progress_bp.route("/chapter/<chapter_id>", methods=["GET"])
@jwt_required()
def get_chapter_progress(chapter_id):
    """
    Récupérer ma progression pour un chapitre spécifique
    ---
    tags:
      - User Progress
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
        description: ID du chapitre
        example: "507f1f77bcf86cd799439020"
    responses:
      200:
        description: Progression du chapitre récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Progression du chapitre récupérée avec succès"
            data:
              type: object
              properties:
                chapter_id:
                  type: string
                status:
                  type: string
                  enum: [not_started, in_progress, completed]
                is_unlocked:
                  type: boolean
                  example: true
                unlocked_at:
                  type: string
                  format: date-time
                unlocked_by:
                  type: string
                  example: "auto"
                quizzes_progress:
                  type: array
                  description: Progression des quiz du chapitre
                  items:
                    type: object
                    properties:
                      quiz_id:
                        type: string
                      attempts_count:
                        type: integer
                      best_score:
                        type: number
                      best_attempt_id:
                        type: string
                      last_attempt_at:
                        type: string
                        format: date-time
                      status:
                        type: string
                        enum: [not_attempted, failed, passed]
                completion_percentage:
                  type: number
                  example: 75.0
                avg_score:
                  type: number
                  example: 82.5
                chapter_info:
                  type: object
                  description: Informations du chapitre
                  properties:
                    title:
                      type: string
                      example: "La Foi"
                    description:
                      type: string
                    order:
                      type: integer
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Progression ou chapitre non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        chapter_prog = get_chapter_progress_service(
            current_user_id, 
            str(user["church_id"]), 
            chapter_id
        )
        
        return jsonify({
            "message": "Progression du chapitre récupérée avec succès",
            "data": chapter_prog
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@user_progress_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def get_dashboard():
    """
    Récupérer les statistiques du dashboard
    ---
    tags:
      - User Progress
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
    responses:
      200:
        description: Statistiques du dashboard récupérées avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Statistiques récupérées avec succès"
            data:
              type: object
              properties:
                overall_stats:
                  type: object
                  description: Statistiques globales
                  properties:
                    total_quiz_completed:
                      type: integer
                      example: 25
                    total_quiz_passed:
                      type: integer
                      example: 20
                    avg_score:
                      type: number
                      example: 78.5
                    total_time_spent_seconds:
                      type: integer
                      example: 21600
                    current_streak_days:
                      type: integer
                      example: 5
                    longest_streak_days:
                      type: integer
                      example: 12
                sections:
                  type: object
                  properties:
                    total:
                      type: integer
                      example: 5
                    completed:
                      type: integer
                      example: 2
                    completion_rate:
                      type: number
                      example: 40.0
                chapters:
                  type: object
                  properties:
                    total:
                      type: integer
                      example: 20
                    unlocked:
                      type: integer
                      example: 15
                    completed:
                      type: integer
                      example: 10
                    completion_rate:
                      type: number
                      example: 50.0
                recent_attempts:
                  type: array
                  description: 5 dernières tentatives
                  items:
                    type: object
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        dashboard = get_dashboard_stats_service(current_user_id, str(user["church_id"]))
        
        return jsonify({
            "message": "Statistiques récupérées avec succès",
            "data": dashboard
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@user_progress_bp.route("/learners", methods=["GET"])
@jwt_required()
@admin_required
def get_learners_progress():
    """
    Récupérer la progression de tous les apprenants (admin uniquement)
    ---
    tags:
      - User Progress
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: query
        name: section_id
        type: string
        required: false
        description: Filtrer par section spécifique
        example: "507f1f77bcf86cd799439011"
    responses:
      200:
        description: Progression des apprenants récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Progression des apprenants récupérée avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  user_id:
                    type: string
                  name:
                    type: string
                  first_name:
                    type: string
                  email:
                    type: string
                  overall_stats:
                    type: object
                  sections_progress:
                    type: array
            total:
              type: integer
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis)
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        section_id = request.args.get("section_id")
        
        learners = get_learners_progress_service(str(user["church_id"]), section_id)
        
        return jsonify({
            "message": "Progression des apprenants récupérée avec succès",
            "data": learners,
            "total": len(learners)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@user_progress_bp.route("/unlock-chapter", methods=["POST"])
@jwt_required()
@admin_required
def manual_unlock_chapter():
    """
    Débloquer manuellement un chapitre pour un apprenant (admin uniquement)
    ---
    tags:
      - User Progress
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
        description: Informations de déblocage
        schema:
          type: object
          required:
            - user_id
            - chapter_id
          properties:
            user_id:
              type: string
              example: "507f1f77bcf86cd799439013"
              description: ID de l'apprenant
            chapter_id:
              type: string
              example: "507f1f77bcf86cd799439020"
              description: ID du chapitre à débloquer
            reason:
              type: string
              example: "Étudiant avancé, passage direct au niveau 2"
              description: Raison du déblocage manuel
    responses:
      200:
        description: Chapitre débloqué avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Chapitre débloqué avec succès"
            chapter_id:
              type: string
            user_id:
              type: string
      400:
        description: Données invalides
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis)
      404:
        description: Chapitre ou utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Valider
        errors = ManualUnlockSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        admin_user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not admin_user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = manual_unlock_chapter_service(
            current_user_id,
            data["user_id"],
            str(admin_user["church_id"]),
            data["chapter_id"],
            data.get("reason")
        )
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@user_progress_bp.route("/leaderboard", methods=["GET"])
@jwt_required()
def get_leaderboard():
    """
    Récupérer le classement des apprenants
    ---
    tags:
      - User Progress
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: query
        name: section_id
        type: string
        required: false
        description: Filtrer par section spécifique
        example: "507f1f77bcf86cd799439011"
      - in: query
        name: limit
        type: integer
        required: false
        default: 10
        description: Nombre de résultats à retourner
        example: 10
    responses:
      200:
        description: Classement récupéré avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Classement récupéré avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  user_id:
                    type: string
                  name:
                    type: string
                    example: "Dupont"
                  first_name:
                    type: string
                    example: "Jean"
                  total_quiz_completed:
                    type: integer
                    example: 25
                  total_quiz_passed:
                    type: integer
                    example: 20
                  avg_score:
                    type: number
                    example: 85.5
                  current_streak_days:
                    type: integer
                    example: 7
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        section_id = request.args.get("section_id")
        limit = int(request.args.get("limit", 10))
        
        leaderboard = get_leaderboard_service(str(user["church_id"]), section_id, limit)
        
        return jsonify({
            "message": "Classement récupéré avec succès",
            "data": leaderboard
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@user_progress_bp.route("/reset", methods=["POST"])
@jwt_required()
@admin_required
def reset_progress():
    """
    Réinitialiser la progression d'un apprenant (admin uniquement)
    ---
    tags:
      - User Progress
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
        description: Utilisateur et section à réinitialiser
        schema:
          type: object
          required:
            - user_id
          properties:
            user_id:
              type: string
              example: "507f1f77bcf86cd799439013"
              description: ID de l'apprenant
            section_id:
              type: string
              example: "507f1f77bcf86cd799439011"
              description: ID de la section (optionnel, si absent réinitialise tout)
    responses:
      200:
        description: Progression réinitialisée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Progression complète réinitialisée"
      400:
        description: Données invalides
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis)
      404:
        description: Progression non trouvée
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        if not data.get("user_id"):
            return jsonify({"message": "user_id est requis"}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        admin_user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not admin_user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = reset_user_progress_service(
            data["user_id"],
            str(admin_user["church_id"]),
            data.get("section_id")
        )
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500
    

# routes/user_progress.py

@user_progress_bp.route("/current-section", methods=["GET"])
@jwt_required()
def get_current_section():
    """
    Récupérer la section actuellement en cours
    ---
    tags:
      - User Progress
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
    responses:
      200:
        description: Section courante récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Section courante récupérée avec succès"
            data:
              type: object
              properties:
                section:
                  type: object
                  properties:
                    _id:
                      type: string
                      example: "507f1f77bcf86cd799439011"
                    title:
                      type: string
                      example: "Nouveau Converti"
                    description:
                      type: string
                      example: "Formation de base pour les nouveaux convertis"
                    is_sequential:
                      type: boolean
                      example: true
                    order:
                      type: integer
                      example: 1
                progress:
                  type: object
                  properties:
                    status:
                      type: string
                      enum: [not_started, in_progress, completed]
                      example: "in_progress"
                    completion_percentage:
                      type: number
                      example: 45.5
                      description: Pourcentage de complétion de la section
                    total_time_spent_seconds:
                      type: integer
                      example: 3600
                      description: Temps total passé en secondes
                    started_at:
                      type: string
                      format: date-time
                    total_chapters:
                      type: integer
                      example: 5
                      description: Nombre total de chapitres
                    completed_chapters:
                      type: integer
                      example: 2
                      description: Nombre de chapitres complétés
                current_chapter:
                  type: object
                  description: Chapitre actuellement en cours ou à faire
                  properties:
                    chapter_id:
                      type: string
                    status:
                      type: string
                    is_unlocked:
                      type: boolean
                    completion_percentage:
                      type: number
                    chapter_info:
                      type: object
                      properties:
                        title:
                          type: string
                          example: "La Foi"
                        description:
                          type: string
                        order:
                          type: integer
                next_chapter:
                  type: object
                  description: Prochain chapitre à débloquer
                  properties:
                    chapter_id:
                      type: string
                    is_unlocked:
                      type: boolean
                    chapter_info:
                      type: object
      404:
        description: Aucune progression trouvée
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Aucune progression trouvée"
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = get_current_section_service(current_user_id, str(user["church_id"]))
        
        if status == 404:
            return jsonify(result), status
        
        return jsonify({
            "message": "Section courante récupérée avec succès",
            "data": result
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@user_progress_bp.route("/next-action", methods=["GET"])
@jwt_required()
def get_next_action():
    """
    Récupérer la prochaine action recommandée
    ---
    tags:
      - User Progress
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
    responses:
      200:
        description: Prochaine action recommandée
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Prochaine action récupérée avec succès"
            data:
              type: object
              properties:
                action:
                  type: string
                  enum: [start_first_section, start_section, read_chapter, take_quiz, all_completed, no_content]
                  example: "take_quiz"
                  description: Type d'action recommandée
                message:
                  type: string
                  example: "Continuez avec le quiz : Test de connaissance - La Foi"
                chapter:
                  type: object
                  description: Chapitre concerné (si applicable)
                  properties:
                    _id:
                      type: string
                    title:
                      type: string
                quiz:
                  type: object
                  description: Quiz à passer (si action = take_quiz)
                  properties:
                    _id:
                      type: string
                    title:
                      type: string
                section:
                  type: object
                  description: Section concernée (si action = start_section)
                  properties:
                    _id:
                      type: string
                    title:
                      type: string
                    description:
                      type: string
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = get_recommended_next_action_service(current_user_id, str(user["church_id"]))
        
        return jsonify({
            "message": "Prochaine action récupérée avec succès",
            "data": result
        }), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500