# routes/quiz_attempts.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from schemas.quiz_attempt_schema import (
    StartQuizAttemptSchema,
    SubmitQuizAttemptSchema,
    UpdateAnswerSchema
)
from services.quiz_attempt_service import (
    get_attempt_with_questions_service,
    start_quiz_attempt_service,
    submit_quiz_attempt_service,
    get_user_attempts_service,
    get_attempt_by_id_service,
    abandon_attempt_service
)
from models.quiz_attempt_model import QuizAttemptModel
from services.quiz_service import get_quiz_last_attempt_service, get_quizzes_with_last_attempt

quiz_attempts_bp = Blueprint("quiz_attempts", __name__, url_prefix="/api/quiz-attempts")


@quiz_attempts_bp.route("/start", methods=["POST"])
@jwt_required()
def start_attempt():
    """
    Démarrer une nouvelle tentative de quiz
    ---
    tags:
      - Quiz Attempts
    consumes:
      - application/json
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
        description: ID du quiz à commencer
        schema:
          type: object
          required:
            - quiz_id
          properties:
            quiz_id:
              type: string
              example: "507f1f77bcf86cd799439030"
              description: ID du quiz à démarrer
    responses:
      201:
        description: Tentative démarrée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Tentative démarrée avec succès"
            attempt_id:
              type: string
              example: "507f1f77bcf86cd799439040"
              description: ID de la tentative créée
            quiz:
              type: object
              description: Informations du quiz (sans les réponses correctes)
              properties:
                _id:
                  type: string
                  example: "507f1f77bcf86cd799439030"
                title:
                  type: string
                  example: "Test de connaissance - La Foi"
                description:
                  type: string
                settings:
                  type: object
                  properties:
                    time_limit_minutes:
                      type: integer
                      example: 30
                    pass_score:
                      type: integer
                      example: 70
                    shuffle_questions:
                      type: boolean
                      example: true
                    shuffle_options:
                      type: boolean
                      example: true
                questions:
                  type: array
                  description: Questions sans les réponses correctes
                  items:
                    type: object
      400:
        description: Données invalides
      403:
        description: Nombre maximum de tentatives atteint
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Nombre maximum de tentatives atteint (3)"
            attempts_used:
              type: integer
              example: 3
      404:
        description: Quiz non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Valider
        errors = StartQuizAttemptSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        # Récupérer l'utilisateur courant
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Démarrer la tentative
        result, status = start_quiz_attempt_service(
            data["quiz_id"],
            current_user_id,
            str(user["church_id"])
        )
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quiz_attempts_bp.route("/submit", methods=["POST"])
@jwt_required()
def submit_attempt():
    """
    Soumettre une tentative de quiz complétée
    ---
    tags:
      - Quiz Attempts
    consumes:
      - application/json
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
        description: Tentative et réponses à soumettre
        schema:
          type: object
          required:
            - attempt_id
            - answers
          properties:
            attempt_id:
              type: string
              example: "507f1f77bcf86cd799439040"
              description: ID de la tentative en cours
            answers:
              type: array
              description: Liste des réponses de l'utilisateur
              items:
                type: object
                required:
                  - question_id
                  - question_type
                properties:
                  question_id:
                    type: string
                    example: "507f1f77bcf86cd799439041"
                    description: ID de la question
                  question_type:
                    type: string
                    enum: [mcq_single, mcq_multiple, true_false, fill_blank, free_text]
                    example: "mcq_single"
                  selected_options:
                    type: array
                    description: IDs des options sélectionnées (pour QCM)
                    items:
                      type: string
                    example: ["507f1f77bcf86cd799439042"]
                  fill_blank_answers:
                    type: array
                    description: Réponses pour compléter la phrase
                    items:
                      type: string
                    example: ["entend", "entend"]
                  free_text_answer:
                    type: string
                    description: Réponse libre
                    example: "Une ferme assurance"
                  time_spent_seconds:
                    type: integer
                    description: Temps passé sur cette question
                    example: 45
    responses:
      200:
        description: Tentative soumise et évaluée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Tentative soumise avec succès"
            data:
              type: object
              description: Tentative complète avec les réponses évaluées
              properties:
                _id:
                  type: string
                  example: "507f1f77bcf86cd799439040"
                quiz_id:
                  type: string
                status:
                  type: string
                  example: "completed"
                score:
                  type: number
                  example: 85.5
                  description: Score en pourcentage
                passed:
                  type: boolean
                  example: true
                time_spent_seconds:
                  type: integer
                  example: 1800
                answers:
                  type: array
                  description: Réponses avec correction
                  items:
                    type: object
                    properties:
                      question_id:
                        type: string
                      is_correct:
                        type: boolean
                        example: true
                      points_earned:
                        type: integer
                        example: 10
                      points_possible:
                        type: integer
                        example: 10
            result:
              type: object
              description: Résumé des résultats
              properties:
                score:
                  type: number
                  example: 85.5
                  description: Score en pourcentage
                max_score:
                  type: integer
                  example: 100
                points_earned:
                  type: integer
                  example: 85
                  description: Points réels obtenus
                points_possible:
                  type: integer
                  example: 100
                  description: Points totaux possibles
                passed:
                  type: boolean
                  example: true
                pass_score:
                  type: integer
                  example: 70
                  description: Score minimum requis
      400:
        description: Données invalides ou tentative déjà soumise
      403:
        description: Accès non autorisé à cette tentative
      404:
        description: Tentative ou quiz non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Valider
        errors = SubmitQuizAttemptSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        # Récupérer l'utilisateur courant
        current_user_id = get_jwt_identity()
        
        # Soumettre la tentative
        result, status = submit_quiz_attempt_service(
            data["attempt_id"],
            data["answers"],
            current_user_id
        )
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quiz_attempts_bp.route("/my-attempts", methods=["GET"])
@jwt_required()
def get_my_attempts():
    """
    Récupérer toutes mes tentatives de quiz
    ---
    tags:
      - Quiz Attempts
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: query
        name: quiz_id
        type: string
        required: false
        description: Filtrer par quiz spécifique
        example: "507f1f77bcf86cd799439030"
    responses:
      200:
        description: Liste des tentatives récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Tentatives récupérées avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "507f1f77bcf86cd799439040"
                  quiz_id:
                    type: string
                    example: "507f1f77bcf86cd799439030"
                  attempt_number:
                    type: integer
                    example: 1
                  status:
                    type: string
                    enum: [in_progress, completed, abandoned]
                    example: "completed"
                  score:
                    type: number
                    example: 85.5
                  passed:
                    type: boolean
                    example: true
                  started_at:
                    type: string
                    format: date-time
                  submitted_at:
                    type: string
                    format: date-time
                  time_spent_seconds:
                    type: integer
                    example: 1800
            total:
              type: integer
              example: 5
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        quiz_id = request.args.get("quiz_id")
        
        attempts = get_user_attempts_service(current_user_id, quiz_id)
        
        return jsonify({
            "message": "Tentatives récupérées avec succès",
            "data": attempts,
            "total": len(attempts)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quiz_attempts_bp.route("/<attempt_id>", methods=["GET"])
@jwt_required()
def get_attempt(attempt_id):
    """
    Récupérer une tentative spécifique avec les questions et réponses
    ---
    tags:
      - Quiz Attempts
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: attempt_id
        type: string
        required: true
        description: ID de la tentative
        example: "507f1f77bcf86cd799439040"
    responses:
      200:
        description: Tentative récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Tentative récupérée avec succès"
            data:
              type: object
              properties:
                _id:
                  type: string
                  example: "507f1f77bcf86cd799439040"
                quiz_id:
                  type: string
                  example: "507f1f77bcf86cd799439030"
                quiz_title:
                  type: string
                  example: "Test de connaissance - La Foi"
                user_id:
                  type: string
                  example: "507f1f77bcf86cd799439013"
                church_id:
                  type: string
                  example: "507f1f77bcf86cd799439012"
                attempt_number:
                  type: integer
                  example: 1
                status:
                  type: string
                  enum: [in_progress, completed, abandoned]
                  example: "completed"
                started_at:
                  type: string
                  format: date-time
                submitted_at:
                  type: string
                  format: date-time
                time_spent_seconds:
                  type: integer
                  example: 1800
                score:
                  type: number
                  example: 85.5
                max_score:
                  type: integer
                  example: 100
                pass_score:
                  type: integer
                  example: 70
                passed:
                  type: boolean
                  example: true
                questions:
                  type: array
                  description: Questions du quiz avec réponses de l'utilisateur
                  items:
                    type: object
                    properties:
                      question_id:
                        type: string
                        example: "q1"
                      order:
                        type: integer
                        example: 1
                      type:
                        type: string
                        enum: [mcq_single, mcq_multiple, true_false, fill_blank, free_text]
                        example: "mcq_single"
                      question_text:
                        type: string
                        example: "Qu'est-ce que la foi selon Hébreux 11:1?"
                      points_possible:
                        type: integer
                        example: 10
                      options:
                        type: array
                        description: Options pour MCQ et True/False
                        items:
                          type: object
                          properties:
                            text:
                              type: string
                            is_correct:
                              type: boolean
                            is_selected:
                              type: boolean
                              description: Option sélectionnée par l'utilisateur
                      user_answer:
                        type: object
                        description: Réponse de l'utilisateur
                        properties:
                          selected_options:
                            type: array
                            items:
                              type: string
                            description: IDs des options sélectionnées
                          text_answer:
                            type: string
                            description: Réponse textuelle (fill_blank, free_text)
                          fill_blank_answers:
                            type: array
                            items:
                              type: string
                            description: Réponses pour fill_blank
                      is_correct:
                        type: boolean
                        example: true
                      points_earned:
                        type: number
                        example: 10
                      explanation:
                        type: string
                        example: "Hébreux 11:1 définit la foi comme..."
                      media:
                        type: object
                        properties:
                          type:
                            type: string
                          url:
                            type: string
                created_at:
                  type: string
                  format: date-time
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès non autorisé à cette tentative
      404:
        description: Tentative non trouvée
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        
        result, status = get_attempt_with_questions_service(attempt_id, current_user_id)
        
        if status != 200:
            return jsonify(result), status
        
        return jsonify({
            "message": "Tentative récupérée avec succès",
            "data": result
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500
# @quiz_attempts_bp.route("/<attempt_id>", methods=["GET"])
# @jwt_required()
# def get_attempt(attempt_id):
#     """
#     Récupérer une tentative spécifique par son ID
#     ---
#     tags:
#       - Quiz Attempts
#     parameters:
#       - in: header
#         name: Authorization
#         required: true
#         schema:
#           type: string
#         description: Token JWT de l'utilisateur
#         example: "Bearer votre.jwt.token"
#       - in: path
#         name: attempt_id
#         type: string
#         required: true
#         description: ID de la tentative
#         example: "507f1f77bcf86cd799439040"
#     responses:
#       200:
#         description: Tentative récupérée avec succès
#         schema:
#           type: object
#           properties:
#             message:
#               type: string
#               example: "Tentative récupérée avec succès"
#             data:
#               type: object
#               properties:
#                 _id:
#                   type: string
#                   example: "507f1f77bcf86cd799439040"
#                 quiz_id:
#                   type: string
#                   example: "507f1f77bcf86cd799439030"
#                 user_id:
#                   type: string
#                   example: "507f1f77bcf86cd799439013"
#                 church_id:
#                   type: string
#                   example: "507f1f77bcf86cd799439012"
#                 attempt_number:
#                   type: integer
#                   example: 1
#                 status:
#                   type: string
#                   enum: [in_progress, completed, abandoned]
#                   example: "completed"
#                 started_at:
#                   type: string
#                   format: date-time
#                 submitted_at:
#                   type: string
#                   format: date-time
#                 time_spent_seconds:
#                   type: integer
#                   example: 1800
#                 score:
#                   type: number
#                   example: 85.5
#                 max_score:
#                   type: integer
#                   example: 100
#                 pass_score:
#                   type: integer
#                   example: 70
#                 passed:
#                   type: boolean
#                   example: true
#                 answers:
#                   type: array
#                   description: Réponses détaillées avec correction
#                   items:
#                     type: object
#                     properties:
#                       question_id:
#                         type: string
#                       question_type:
#                         type: string
#                       selected_options:
#                         type: array
#                         items:
#                           type: string
#                       is_correct:
#                         type: boolean
#                       points_earned:
#                         type: integer
#                       points_possible:
#                         type: integer
#                 created_at:
#                   type: string
#                   format: date-time
#       401:
#         description: Token JWT manquant ou invalide
#       403:
#         description: Accès non autorisé à cette tentative
#       404:
#         description: Tentative non trouvée
#       500:
#         description: Erreur serveur
#     """
#     try:
#         current_user_id = get_jwt_identity()
        
#         result, status = get_attempt_by_id_service(attempt_id, current_user_id)
        
#         if status != 200:
#             return jsonify(result), status
        
#         return jsonify({
#             "message": "Tentative récupérée avec succès",
#             "data": result
#         }), 200
        
#     except Exception as e:
#         return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quiz_attempts_bp.route("/<attempt_id>/abandon", methods=["POST"])
@jwt_required()
def abandon_attempt(attempt_id):
    """
    Abandonner une tentative en cours
    ---
    tags:
      - Quiz Attempts
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: attempt_id
        type: string
        required: true
        description: ID de la tentative à abandonner
        example: "507f1f77bcf86cd799439040"
    responses:
      200:
        description: Tentative abandonnée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Tentative abandonnée"
      400:
        description: Cette tentative ne peut pas être abandonnée (déjà complétée ou abandonnée)
      403:
        description: Accès non autorisé à cette tentative
      404:
        description: Tentative non trouvée
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        
        result, status = abandon_attempt_service(attempt_id, current_user_id)
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quiz_attempts_bp.route("/quiz/<quiz_id>/attempts", methods=["GET"])
@jwt_required()
def get_quiz_attempts(quiz_id):
    """
    Récupérer toutes les tentatives d'un quiz (admin uniquement)
    ---
    tags:
      - Quiz Attempts
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: quiz_id
        type: string
        required: true
        description: ID du quiz
        example: "507f1f77bcf86cd799439030"
      - in: query
        name: status
        type: string
        required: false
        description: Filtrer par statut
        enum: [in_progress, completed, abandoned]
        example: "completed"
    responses:
      200:
        description: Liste des tentatives récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Tentatives du quiz récupérées avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                  user_id:
                    type: string
                  attempt_number:
                    type: integer
                  status:
                    type: string
                  score:
                    type: number
                  passed:
                    type: boolean
                  started_at:
                    type: string
                    format: date-time
                  submitted_at:
                    type: string
                    format: date-time
            total:
              type: integer
              example: 45
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
        
        # Vérifier que l'utilisateur est admin
        if user.get("role") not in ["admin", "leader"]:
            return jsonify({"message": "Accès refusé. Admin requis."}), 403
        
        # Récupérer toutes les tentatives du quiz
        attempts = list(QuizAttemptModel.get_collection().find({
            "quiz_id": ObjectId(quiz_id),
            "church_id": user["church_id"]
        }).sort("created_at", -1))
        
        # Filtrer par statut si spécifié
        status_filter = request.args.get("status")
        if status_filter:
            attempts = [a for a in attempts if a.get("status") == status_filter]
        
        # Convertir les ObjectId
        for attempt in attempts:
            attempt["_id"] = str(attempt["_id"])
            attempt["quiz_id"] = str(attempt["quiz_id"])
            attempt["user_id"] = str(attempt["user_id"])
            attempt["church_id"] = str(attempt["church_id"])
            
            # Convertir les ObjectId dans les réponses
            for answer in attempt.get("answers", []):
                answer["question_id"] = str(answer["question_id"])
                if "selected_options" in answer:
                    answer["selected_options"] = [str(opt_id) for opt_id in answer["selected_options"]]
        
        return jsonify({
            "message": "Tentatives du quiz récupérées avec succès",
            "data": attempts,
            "total": len(attempts)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quiz_attempts_bp.route("/stats/user", methods=["GET"])
@jwt_required()
def get_user_stats():
    """
    Récupérer les statistiques globales de l'utilisateur
    ---
    tags:
      - Quiz Attempts
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
                total_attempts:
                  type: integer
                  example: 25
                  description: Nombre total de tentatives complétées
                passed_attempts:
                  type: integer
                  example: 20
                  description: Nombre de tentatives réussies
                pass_rate:
                  type: number
                  example: 80.0
                  description: Taux de réussite en pourcentage
                avg_score:
                  type: number
                  example: 82.5
                  description: Score moyen
                total_time_hours:
                  type: number
                  example: 12.5
                  description: Temps total passé en heures
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
        
        # Récupérer les stats
        stats = QuizAttemptModel.get_user_stats(current_user_id, str(user["church_id"]))
        
        if not stats:
            return jsonify({
                "message": "Aucune tentative complétée",
                "data": {
                    "total_attempts": 0,
                    "passed_attempts": 0,
                    "pass_rate": 0,
                    "avg_score": 0,
                    "total_time_hours": 0
                }
            }), 200
        
        return jsonify({
            "message": "Statistiques récupérées avec succès",
            "data": {
                "total_attempts": stats.get("total_attempts", 0),
                "passed_attempts": stats.get("passed_attempts", 0),
                "pass_rate": round((stats.get("passed_attempts", 0) / stats.get("total_attempts", 1)) * 100, 2),
                "avg_score": round(stats.get("avg_score", 0), 2),
                "total_time_hours": round(stats.get("total_time", 0) / 3600, 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500
    
 
@quiz_attempts_bp.route("/chapter/<chapter_id>/last-attempts", methods=["GET"])
@jwt_required()
def get_quizzes_last_attempts(chapter_id):
    """
    Récupère tous les quiz d'un chapitre et pour chaque quiz,
    la dernière tentative de l'utilisateur connecté.
    ---
    tags:
      - Quizzes
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
        example: "507f1f77bcf86cd799439011"
    responses:
      200:
        description: Liste des quiz avec la dernière tentative
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Quiz récupérés avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  quiz:
                    type: object
                    description: Quiz sans réponses correctes (mode apprenant)
                  last_attempt:
                    type: object
                    description: Dernière tentative de l'utilisateur pour ce quiz
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Chapitre ou quiz non trouvé
      500:
        description: Erreur serveur
    """
    
    try:
        current_user_id = get_jwt_identity()
        
        quizzes_with_attempts = get_quizzes_with_last_attempt(chapter_id, current_user_id)
        
        if not quizzes_with_attempts:
            return jsonify({"message": "Aucun quiz trouvé pour ce chapitre"}), 404
        
        return jsonify({
            "message": "Quiz récupérés avec succès",
            "data": quizzes_with_attempts
        }), 200
    
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500
    

@quiz_attempts_bp.route("/quiz/<quiz_id>/last-attempt", methods=["GET"])
@jwt_required()
def get_quiz_last_attempt(quiz_id):
    """
    Récupère la dernière tentative d'un utilisateur pour un quiz spécifique
    avec toutes les questions et réponses détaillées
    ---
    tags:
      - Quiz Attempts
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: quiz_id
        type: string
        required: true
        description: ID du quiz
        example: "690abc789def012345678901"
    responses:
      200:
        description: Dernière tentative récupérée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Dernière tentative récupérée avec succès"
            data:
              type: object
              properties:
                quiz:
                  type: object
                  description: Informations du quiz
                last_attempt:
                  type: object
                  description: Dernière tentative avec scores
                questions:
                  type: array
                  description: Questions avec réponses de l'utilisateur
                has_attempt:
                  type: boolean
                completion_status:
                  type: string
                  enum: [not_started, partially_answered, fully_answered]
                summary:
                  type: object
                  description: Résumé de la complétion
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Quiz non trouvé ou aucune tentative
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        
        result = get_quiz_last_attempt_service(quiz_id, current_user_id)
        
        if not result:
            return jsonify({"message": "Quiz non trouvé"}), 404
        
        return jsonify({
            "message": "Dernière tentative récupérée avec succès",
            "data": result
        }), 200
    
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


