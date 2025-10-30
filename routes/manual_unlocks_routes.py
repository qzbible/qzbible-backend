# routes/manual_unlocks.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime
from schemas.manual_unlock_schema import ManualUnlockFilterSchema
from services.manual_unlock_service import (
    get_all_unlocks_service,
    get_unlocks_by_learner_service,
    get_unlocks_by_chapter_service,
    get_unlock_stats_service,
    delete_unlock_service
)
from utils.decorators import admin_required

manual_unlocks_bp = Blueprint("manual_unlocks", __name__, url_prefix="/api/manual-unlocks")


@manual_unlocks_bp.route("/list", methods=["GET"])
@jwt_required()
@admin_required
def list_unlocks():
    """
    Récupérer tous les déblocages manuels de l'église (admin uniquement)
    ---
    tags:
      - Manual Unlocks
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: query
        name: learner_id
        type: string
        required: false
        description: Filtrer par apprenant spécifique
        example: "507f1f77bcf86cd799439013"
      - in: query
        name: chapter_id
        type: string
        required: false
        description: Filtrer par chapitre spécifique
        example: "507f1f77bcf86cd799439020"
      - in: query
        name: unlocked_by
        type: string
        required: false
        description: Filtrer par leader qui a débloqué
        example: "507f1f77bcf86cd799439014"
      - in: query
        name: start_date
        type: string
        format: date-time
        required: false
        description: Date de début du filtre
        example: "2025-01-01T00:00:00Z"
      - in: query
        name: end_date
        type: string
        format: date-time
        required: false
        description: Date de fin du filtre
        example: "2025-12-31T23:59:59Z"
    responses:
      200:
        description: Liste des déblocages récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Déblocages récupérés avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "507f1f77bcf86cd799439050"
                  church_id:
                    type: string
                  learner_id:
                    type: string
                  learner_name:
                    type: string
                    example: "Dupont"
                  learner_first_name:
                    type: string
                    example: "Jean"
                  learner_email:
                    type: string
                    example: "jean.dupont@example.com"
                  chapter_id:
                    type: string
                  chapter_title:
                    type: string
                    example: "La Foi"
                  chapter_order:
                    type: integer
                    example: 2
                  section_id:
                    type: string
                  section_title:
                    type: string
                    example: "Nouveau Converti"
                  unlocked_by:
                    type: string
                  leader_name:
                    type: string
                    example: "Martin"
                  leader_first_name:
                    type: string
                    example: "Pierre"
                  leader_role:
                    type: string
                    example: "leader"
                  reason:
                    type: string
                    example: "Étudiant avancé, passage direct au niveau 2"
                  created_at:
                    type: string
                    format: date-time
            total:
              type: integer
              example: 15
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
        
        # Préparer les filtres
        filters = {}
        if request.args.get("learner_id"):
            filters["learner_id"] = request.args.get("learner_id")
        if request.args.get("chapter_id"):
            filters["chapter_id"] = request.args.get("chapter_id")
        if request.args.get("unlocked_by"):
            filters["unlocked_by"] = request.args.get("unlocked_by")
        if request.args.get("start_date"):
            try:
                filters["start_date"] = datetime.fromisoformat(request.args.get("start_date").replace('Z', '+00:00'))
            except:
                pass
        if request.args.get("end_date"):
            try:
                filters["end_date"] = datetime.fromisoformat(request.args.get("end_date").replace('Z', '+00:00'))
            except:
                pass
        
        unlocks = get_all_unlocks_service(str(user["church_id"]), filters if filters else None)
        
        return jsonify({
            "message": "Déblocages récupérés avec succès",
            "data": unlocks,
            "total": len(unlocks)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@manual_unlocks_bp.route("/learner/<learner_id>", methods=["GET"])
@jwt_required()
@admin_required
def get_unlocks_by_learner(learner_id):
    """
    Récupérer tous les déblocages d'un apprenant spécifique
    ---
    tags:
      - Manual Unlocks
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: learner_id
        type: string
        required: true
        description: ID de l'apprenant
        example: "507f1f77bcf86cd799439013"
    responses:
      200:
        description: Déblocages de l'apprenant récupérés avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Déblocages de l'apprenant récupérés avec succès"
            data:
              type: array
              items:
                type: object
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
        
        unlocks = get_unlocks_by_learner_service(learner_id, str(user["church_id"]))
        
        return jsonify({
            "message": "Déblocages de l'apprenant récupérés avec succès",
            "data": unlocks,
            "total": len(unlocks)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@manual_unlocks_bp.route("/chapter/<chapter_id>", methods=["GET"])
@jwt_required()
@admin_required
def get_unlocks_by_chapter(chapter_id):
    """
    Récupérer tous les déblocages pour un chapitre spécifique
    ---
    tags:
      - Manual Unlocks
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
        description: ID du chapitre
        example: "507f1f77bcf86cd799439020"
    responses:
      200:
        description: Déblocages du chapitre récupérés avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Déblocages du chapitre récupérés avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                  learner_id:
                    type: string
                  learner_name:
                    type: string
                  learner_first_name:
                    type: string
                  learner_email:
                    type: string
                  unlocked_by:
                    type: string
                  leader_name:
                    type: string
                  leader_first_name:
                    type: string
                  reason:
                    type: string
                  created_at:
                    type: string
                    format: date-time
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
        
        unlocks = get_unlocks_by_chapter_service(chapter_id, str(user["church_id"]))
        
        return jsonify({
            "message": "Déblocages du chapitre récupérés avec succès",
            "data": unlocks,
            "total": len(unlocks)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@manual_unlocks_bp.route("/stats", methods=["GET"])
@jwt_required()
@admin_required
def get_unlock_stats():
    """
    Récupérer les statistiques des déblocages manuels
    ---
    tags:
      - Manual Unlocks
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
    responses:
      200:
        description: Statistiques récupérées avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Statistiques récupérées avec succès"
            data:
              type: object
              properties:
                global_stats:
                  type: object
                  properties:
                    total_unlocks:
                      type: integer
                      example: 45
                      description: Nombre total de déblocages
                    unique_learners_count:
                      type: integer
                      example: 20
                      description: Nombre d'apprenants ayant bénéficié de déblocages
                    unique_leaders_count:
                      type: integer
                      example: 5
                      description: Nombre de leaders ayant effectué des déblocages
                most_unlocked_chapters:
                  type: array
                  description: Top 5 des chapitres les plus débloqués
                  items:
                    type: object
                    properties:
                      chapter_id:
                        type: string
                      chapter_title:
                        type: string
                        example: "L'Évangélisation"
                      section_id:
                        type: string
                      unlock_count:
                        type: integer
                        example: 12
                      unique_learners_count:
                        type: integer
                        example: 8
                most_active_leaders:
                  type: array
                  description: Top 5 des leaders les plus actifs
                  items:
                    type: object
                    properties:
                      leader_id:
                        type: string
                      leader_name:
                        type: string
                        example: "Martin"
                      leader_first_name:
                        type: string
                        example: "Pierre"
                      leader_role:
                        type: string
                        example: "leader"
                      unlock_count:
                        type: integer
                        example: 15
                      unique_learners_count:
                        type: integer
                        example: 10
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
        
        stats = get_unlock_stats_service(str(user["church_id"]))
        
        return jsonify({
            "message": "Statistiques récupérées avec succès",
            "data": stats
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@manual_unlocks_bp.route("/<unlock_id>/delete", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_unlock(unlock_id):
    """
    Supprimer un enregistrement de déblocage manuel (correction d'erreur)
    ---
    tags:
      - Manual Unlocks
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: unlock_id
        type: string
        required: true
        description: ID du déblocage à supprimer
        example: "507f1f77bcf86cd799439050"
    responses:
      200:
        description: Déblocage supprimé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Déblocage supprimé avec succès"
            deleted_count:
              type: integer
              example: 1
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis ou déblocage d'une autre église)
      404:
        description: Déblocage non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = delete_unlock_service(unlock_id, str(user["church_id"]))
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@manual_unlocks_bp.route("/my-unlocks", methods=["GET"])
@jwt_required()
def get_my_unlocks():
    """
    Récupérer mes propres déblocages manuels (apprenant)
    ---
    tags:
      - Manual Unlocks
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
        description: Mes déblocages récupérés avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Vos déblocages récupérés avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                  chapter_id:
                    type: string
                  chapter_title:
                    type: string
                  section_id:
                    type: string
                  leader_name:
                    type: string
                  leader_first_name:
                    type: string
                  reason:
                    type: string
                  created_at:
                    type: string
                    format: date-time
            total:
              type: integer
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
        
        unlocks = get_unlocks_by_learner_service(current_user_id, str(user["church_id"]))
        
        return jsonify({
            "message": "Vos déblocages récupérés avec succès",
            "data": unlocks,
            "total": len(unlocks)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500