# routes/reading_plan.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
import os
from werkzeug.utils import secure_filename

from schemas.reading_plan_schema import *
from services.reading_plan_service import *
from utils.decorators import admin_required

reading_plan_bp = Blueprint("reading_plan", __name__, url_prefix="/api/reading-plans")
documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")

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
        type: string
        required: false
        enum: [bible, books, study, mixed]
        description: Filtrer par catégorie
        example: "bible"
      - in: query
        name: difficulty
        type: string
        required: false
        enum: [beginner, intermediate, advanced]
        description: Filtrer par niveau de difficulté
        example: "beginner"
      - in: query
        name: creator_type
        type: string
        required: false
        enum: [admin, pastor, user]
        description: Filtrer par type de créateur
        example: "admin"
      - in: query
        name: duration_range
        type: string
        required: false
        description: Filtrer par durée (format min-max)
        example: "7-30"
      - in: query
        name: tags
        type: string
        required: false
        description: Filtrer par tags (séparés par des virgules)
        example: "baptême,nouveau-converti"
      - in: query
        name: search
        type: string
        required: false
        description: Recherche textuelle
        example: "formation"
      - in: query
        name: sort_by
        type: string
        required: false
        enum: [created_at, popular, rating]
        default: created_at
        description: Critère de tri
        example: "popular"
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
        description: Plans de lecture récupérés avec succès
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
                  stats:
                    type: object
                    properties:
                      subscribers:
                        type: integer
                      completions:
                        type: integer
                      average_rating:
                        type: number
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

@reading_plan_bp.route("", methods=["POST"])
@jwt_required()
def create_reading_plan():
    """
    Créer un nouveau plan de lecture
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

# Routes pour les documents
@documents_bp.route("/upload", methods=["POST"])
@jwt_required()
@admin_required
def upload_document():
    """
    Upload d'un document PDF (admin uniquement)
    """
    try:
        if 'file' not in request.files:
            return jsonify({"message": "Aucun fichier fourni"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"message": "Aucun fichier sélectionné"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"message": "Seuls les fichiers PDF sont autorisés"}), 400
        
        # Valider les métadonnées
        metadata = {
            'title': request.form.get('title'),
            'author': request.form.get('author'),
            'category': request.form.get('category'),
            'language': request.form.get('language', 'fr'),
            'description': request.form.get('description', ''),
            'visibility': request.form.get('visibility', 'public')
        }
        
        errors = DocumentCreateSchema().validate(metadata)
        if errors:
            return jsonify({"errors": errors}), 400
        
        # Sauvegarder le fichier
        filename = secure_filename(file.filename)
        # Configuration du dossier d'upload à définir dans ton app.py
        upload_path = os.path.join('/path/to/upload/folder', 'documents', filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)
        
        file_info = {
            'original_filename': file.filename,
            'file_path': upload_path,
            'file_size': os.path.getsize(upload_path),
            'mime_type': 'application/pdf',
            'upload_date': datetime.utcnow()
        }
        
        current_user_id = get_jwt_identity()
        result, status = create_document_service(metadata, file_info, current_user_id)
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@documents_bp.route("/<doc_id>/structure", methods=["POST"])
@jwt_required()
@admin_required
def set_document_structure(doc_id):
    """
    Définir la structure d'un document (admin uniquement)
    """
    try:
        data = request.get_json()
        
        # Validation de la structure
        errors = DocumentStructureSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        result, status = update_document_structure_service(doc_id, data)
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@documents_bp.route("/for-plans", methods=["GET"])
@jwt_required()
def get_documents_for_plans():
    """
    Récupérer les documents disponibles pour les plans de lecture
    """
    try:
        filters = {}
        if request.args.get("category"):
            filters["category"] = request.args.get("category")
        if request.args.get("language"):
            filters["language"] = request.args.get("language")
        if request.args.get("has_page_numbers"):
            filters["has_page_numbers"] = request.args.get("has_page_numbers").lower() == 'true'
        if request.args.get("min_pages"):
            filters["min_pages"] = request.args.get("min_pages")
        
        documents = get_documents_for_plans_service(filters)
        
        return jsonify({
            "message": "Documents récupérés avec succès",
            "data": documents,
            "total": len(documents)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@documents_bp.route("/<doc_id>/plan-helper", methods=["GET"])
@jwt_required()
def get_document_plan_helper(doc_id):
    """
    Aide à la configuration d'un plan depuis un document
    """
    try:
        result = get_document_plan_helper_service(doc_id)
        
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        
        return jsonify({
            "message": "Aide à la configuration récupérée avec succès",
            "data": result
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

def register_reading_plan_blueprints(app):
    """Enregistrer les blueprints"""
    app.register_blueprint(reading_plan_bp)
    app.register_blueprint(documents_bp)