# routes/quizzes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from schemas.quiz_schema import CreateQuizSchema, UpdateQuizSchema
from services.quiz_service import (
    create_quiz_service,
    get_all_quizzes_service,
    get_quiz_by_id_service,
    update_quiz_service,
    delete_quiz_service,
    get_quiz_stats_service,
    clone_quiz_service
)
from utils.decorators import admin_required

quizzes_bp = Blueprint("quizzes", __name__, url_prefix="/api/quizzes")


@quizzes_bp.route("/create", methods=["POST"])
@jwt_required()
@admin_required
def create():
    """
    Créer un nouveau quiz avec ses questions
    ---
    tags:
      - Quizzes
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
        description: Données du quiz à créer
        schema:
          type: object
          required:
            - chapter_id
            - title
            - questions
          properties:
            chapter_id:
              type: string
              example: "507f1f77bcf86cd799439020"
              description: ID du chapitre parent
            title:
              type: string
              example: "Test de connaissance - La Foi"
              description: Titre du quiz
            description:
              type: string
              example: "Évaluation des connaissances sur la foi"
              description: Description du quiz
            order:
              type: integer
              example: 1
              description: Ordre d'affichage (auto-calculé si non fourni)
            settings:
              type: object
              properties:
                time_limit_minutes:
                  type: integer
                  example: 30
                  description: Durée limite en minutes
                pass_score:
                  type: integer
                  example: 70
                  description: Score minimum pour réussir (0-100)
                shuffle_questions:
                  type: boolean
                  example: true
                  description: Mélanger l'ordre des questions
                shuffle_options:
                  type: boolean
                  example: true
                  description: Mélanger l'ordre des options
                show_correct_answers:
                  type: boolean
                  example: true
                  description: Afficher les réponses correctes après soumission
                max_attempts:
                  type: integer
                  example: 0
                  description: Nombre maximum de tentatives (0 = illimité)
                allow_review:
                  type: boolean
                  example: true
                  description: Permettre de revoir le quiz après soumission
            questions:
              type: array
              items:
                type: object
                required:
                  - type
                  - order
                  - question_text
                  - points
                properties:
                  type:
                    type: string
                    enum: [mcq_single, mcq_multiple, true_false, fill_blank, free_text]
                    example: "mcq_single"
                    description: Type de question
                  order:
                    type: integer
                    example: 1
                    description: Ordre de la question
                  question_text:
                    type: string
                    example: "Qu'est-ce que la foi selon Hébreux 11:1?"
                    description: Texte de la question
                  points:
                    type: integer
                    example: 10
                    description: Points attribués à cette question
                  options:
                    type: array
                    description: Options pour QCM et Vrai/Faux
                    items:
                      type: object
                      properties:
                        text:
                          type: string
                          example: "Une ferme assurance des choses qu'on espère"
                        is_correct:
                          type: boolean
                          example: true
                        points:
                          type: integer
                          example: 5
                          description: Points pour cette option (mcq_multiple uniquement)
                  fill_blank_text:
                    type: string
                    example: "La foi vient de ce qu'on _____, et ce qu'on _____ vient de la parole de Christ."
                    description: Texte avec espaces à compléter (fill_blank uniquement)
                  correct_answers:
                    type: array
                    items:
                      type: string
                    example: ["entend", "entend"]
                    description: Réponses correctes pour fill_blank
                  free_text_answers:
                    type: array
                    items:
                      type: string
                    example: ["Une ferme assurance", "L'assurance des choses qu'on espère"]
                    description: Variantes de réponses acceptées (free_text uniquement)
                  case_sensitive:
                    type: boolean
                    example: false
                    description: Réponse sensible à la casse (free_text uniquement)
                  explanation:
                    type: string
                    example: "Hébreux 11:1 définit la foi comme..."
                    description: Explication de la réponse
                  media:
                    type: object
                    description: Média associé à la question
                    properties:
                      type:
                        type: string
                        enum: [image, audio, video]
                        example: "image"
                      url:
                        type: string
                        example: "https://example.com/image.jpg"
    responses:
      201:
        description: Quiz créé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Quiz créé avec succès"
            quiz_id:
              type: string
              example: "507f1f77bcf86cd799439030"
      400:
        description: Données invalides
        schema:
          type: object
          properties:
            errors:
              type: object
              example: {"title": ["Le titre est requis"], "questions": ["Au moins une question est requise"]}
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis)
      404:
        description: Chapitre non trouvé
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
        errors = CreateQuizSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        # Créer le quiz
        result, status = create_quiz_service(data)
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quizzes_bp.route("/chapter/<chapter_id>", methods=["GET"])
@jwt_required()
def list_by_chapter(chapter_id):
    """
    Récupérer tous les quiz d'un chapitre
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
        example: "507f1f77bcf86cd799439020"
    responses:
      200:
        description: Liste des quiz récupérée avec succès
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
                  _id:
                    type: string
                    example: "507f1f77bcf86cd799439030"
                  chapter_id:
                    type: string
                    example: "507f1f77bcf86cd799439020"
                  title:
                    type: string
                    example: "Test de connaissance - La Foi"
                  description:
                    type: string
                  order:
                    type: integer
                    example: 1
                  settings:
                    type: object
                  questions:
                    type: array
                    description: Liste des questions (réponses masquées)
                  created_at:
                    type: string
                    format: date-time
            total:
              type: integer
              example: 3
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès non autorisé
      404:
        description: Chapitre non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Vérifier que le chapitre appartient à l'église
        from models.chapter_model import ChapterModel
        chapter = ChapterModel.get_chapter_by_id(chapter_id)
        
        if not chapter:
            return jsonify({"message": "Chapitre non trouvé"}), 404
        
        if chapter["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        quizzes = get_all_quizzes_service(chapter_id)
        
        return jsonify({
            "message": "Quiz récupérés avec succès",
            "data": quizzes,
            "total": len(quizzes)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quizzes_bp.route("/<quiz_id>", methods=["GET"])
@jwt_required()
def get_quiz(quiz_id):
    """
    Récupérer un quiz spécifique par son ID
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
        name: quiz_id
        type: string
        required: true
        description: ID du quiz à récupérer
        example: "507f1f77bcf86cd799439030"
      - in: query
        name: include_answers
        type: boolean
        required: false
        description: Inclure les réponses correctes (admin uniquement)
        example: false
    responses:
      200:
        description: Quiz récupéré avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Quiz récupéré avec succès"
            data:
              type: object
              properties:
                _id:
                  type: string
                  example: "507f1f77bcf86cd799439030"
                chapter_id:
                  type: string
                  example: "507f1f77bcf86cd799439020"
                church_id:
                  type: string
                  example: "507f1f77bcf86cd799439012"
                title:
                  type: string
                  example: "Test de connaissance - La Foi"
                description:
                  type: string
                order:
                  type: integer
                  example: 1
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
                    show_correct_answers:
                      type: boolean
                      example: true
                    max_attempts:
                      type: integer
                      example: 0
                    allow_review:
                      type: boolean
                      example: true
                questions:
                  type: array
                  items:
                    type: object
                    description: Questions (réponses masquées si include_answers=false)
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
        description: Accès non autorisé à ce quiz
      404:
        description: Quiz ou utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Vérifier si on doit inclure les réponses (admin uniquement)
        include_answers = request.args.get("include_answers", "false").lower() == "true"
        if include_answers and user.get("role") not in ["admin", "leader"]:
            include_answers = False
        
        quiz = get_quiz_by_id_service(quiz_id, include_answers=include_answers)
        
        if not quiz:
            return jsonify({"message": "Quiz non trouvé"}), 404
        
        # Vérifier l'accès
        if quiz["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        return jsonify({
            "message": "Quiz récupéré avec succès",
            "data": quiz
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quizzes_bp.route("/<quiz_id>/update", methods=["PUT"])
@jwt_required()
@admin_required
def update_quiz(quiz_id):
    """
    Mettre à jour un quiz existant
    ---
    tags:
      - Quizzes
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
        name: quiz_id
        type: string
        required: true
        description: ID du quiz à mettre à jour
        example: "507f1f77bcf86cd799439030"
      - in: body
        name: body
        required: true
        description: Données à mettre à jour
        schema:
          type: object
          properties:
            title:
              type: string
              example: "Test de connaissance - La Foi (Mise à jour)"
            description:
              type: string
            order:
              type: integer
            settings:
              type: object
            questions:
              type: array
              description: Nouvelle liste complète des questions
              items:
                type: object
    responses:
      200:
        description: Quiz mis à jour avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Quiz mis à jour avec succès"
            modified_count:
              type: integer
              example: 1
      400:
        description: Données de mise à jour invalides
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis ou quiz d'une autre église)
      404:
        description: Quiz ou utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Valider
        errors = UpdateQuizSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        quiz = get_quiz_by_id_service(quiz_id, include_answers=True)
        
        if not quiz:
            return jsonify({"message": "Quiz non trouvé"}), 404
        
        if quiz["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        result = update_quiz_service(quiz_id, data)
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quizzes_bp.route("/<quiz_id>/delete", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_quiz(quiz_id):
    """
    Supprimer un quiz
    ---
    tags:
      - Quizzes
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
        description: ID du quiz à supprimer
        example: "507f1f77bcf86cd799439030"
    responses:
      200:
        description: Quiz supprimé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Quiz supprimé avec succès"
            deleted_count:
              type: integer
              example: 1
      400:
        description: Impossible de supprimer (tentatives enregistrées)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Impossible de supprimer ce quiz. Il a 15 tentative(s) enregistrée(s)."
            attempts_count:
              type: integer
              example: 15
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis ou quiz d'une autre église)
      404:
        description: Quiz ou utilisateur non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        quiz = get_quiz_by_id_service(quiz_id, include_answers=True)
        
        if not quiz:
            return jsonify({"message": "Quiz non trouvé"}), 404
        
        if quiz["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé"}), 403
        
        result, status = delete_quiz_service(quiz_id)
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quizzes_bp.route("/<quiz_id>/stats", methods=["GET"])
@jwt_required()
@admin_required
def get_quiz_stats(quiz_id):
    """
    Récupérer les statistiques d'un quiz
    ---
    tags:
      - Quizzes
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
    responses:
      200:
        description: Statistiques récupérées avec succès
        schema:
          type: object
          properties:
            quiz_id:
              type: string
              example: "507f1f77bcf86cd799439030"
            title:
              type: string
              example: "Test de connaissance - La Foi"
            total_questions:
              type: integer
              example: 10
              description: Nombre total de questions
            total_points:
              type: integer
              example: 100
              description: Points totaux du quiz
            total_attempts:
              type: integer
              example: 45
              description: Nombre total de tentatives
            passed_attempts:
              type: integer
              example: 32
              description: Nombre de tentatives réussies
            pass_rate:
              type: number
              example: 71.11
              description: Taux de réussite en pourcentage
            avg_score:
              type: number
              example: 75.5
              description: Score moyen
            avg_time_minutes:
              type: number
              example: 18.5
              description: Temps moyen en minutes
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis)
      404:
        description: Quiz non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = get_quiz_stats_service(quiz_id)
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@quizzes_bp.route("/<quiz_id>/clone", methods=["POST"])
@jwt_required()
@admin_required
def clone_quiz(quiz_id):
    """
    Cloner un quiz vers un autre chapitre
    ---
    tags:
      - Quizzes
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
        name: quiz_id
        type: string
        required: true
        description: ID du quiz à cloner
        example: "507f1f77bcf86cd799439030"
      - in: body
        name: body
        required: true
        description: Chapitre de destination
        schema:
          type: object
          required:
            - target_chapter_id
          properties:
            target_chapter_id:
              type: string
              example: "507f1f77bcf86cd799439088"
              description: ID du chapitre de destination
    responses:
      201:
        description: Quiz cloné avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Quiz cloné avec succès"
            quiz_id:
              type: string
              example: "507f1f77bcf86cd799439099"
              description: ID du nouveau quiz cloné
      400:
        description: Données invalides
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé
      404:
        description: Quiz ou chapitre non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        if not data.get("target_chapter_id"):
            return jsonify({"message": "target_chapter_id est requis"}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Vérifier que le chapitre cible existe et appartient à l'église
        from models.chapter_model import ChapterModel
        target_chapter = ChapterModel.get_chapter_by_id(data["target_chapter_id"])
        
        if not target_chapter:
            return jsonify({"message": "Chapitre de destination non trouvé"}), 404
        
        if target_chapter["church_id"] != str(user["church_id"]):
            return jsonify({"message": "Accès non autorisé au chapitre de destination"}), 403
        
        result, status = clone_quiz_service(
            quiz_id,
            data["target_chapter_id"],
            str(user["church_id"]),
            current_user_id
        )
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500