# routes/reading_plan.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
import os
from werkzeug.utils import secure_filename
from datetime import datetime

from schemas.reading_plan_schema import *
from services.pdf_extraction_service import extract_pdf_metadata
from services.reading_plan_service import *
from utils.decorators import admin_required

 
documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")

@documents_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():
    """
    Upload d'un document PDF simplifié
    ---
    tags:
      - Documents
    consumes:
      - multipart/form-data
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: formData
        name: file
        type: file
        required: true
        description: Fichier PDF à uploader
    responses:
      201:
        description: Document uploadé avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Document créé avec succès"
                document_id:
                  type: string
                  example: "507f1f77bcf86cd799439060"
                title:
                  type: string
                  example: "La Marche Chrétienne"
                author:
                  type: string
                  example: "Auteur inconnu"
                file_size:
                  type: integer
                  example: 2048576
                absolute_file_path:
                  type: string
                  example: "/var/www/qbible/uploads/documents/la_marche_chretienne.pdf"
      400:
        description: Fichier invalide ou manquant
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        if 'file' not in request.files:
            return jsonify({"message": "Aucun fichier fourni"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"message": "Aucun fichier sélectionné"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"message": "Seuls les fichiers PDF sont autorisés"}), 400
        
        # Sauvegarder le fichier
        filename = secure_filename(file.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{filename}"
        
        from flask import current_app
        upload_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', '/tmp'), 'documents', unique_filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)
        
        # Métadonnées basiques extraites du nom de fichier
        title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
        
        # Métadonnées minimales
        metadata = {
            'title': title,
            'author': 'Auteur inconnu',
            'category': 'study',
            'language': 'fr'
        }
        
        file_info = {
            'original_filename': file.filename,
            'file_path': upload_path,
            'file_size': os.path.getsize(upload_path),
            'upload_date': datetime.utcnow()
        }
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if user and user.get("church_id"):
            metadata['church_id'] = str(user["church_id"])
        
        result, status = create_document_service(metadata, file_info, current_user_id)
        
        # Réponse simplifiée
        response_data = {
            "message": result["message"],
            "document_id": result["document_id"],
            "title": metadata['title'],
            "author": metadata['author'],
            "file_size": file_info['file_size'],
            "absolute_file_path": os.path.abspath(upload_path)
        }
        
        return jsonify(response_data), status
        
    except Exception as e:
        if 'upload_path' in locals() and os.path.exists(upload_path):
            os.remove(upload_path)
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@documents_bp.route("/<doc_id>/structure", methods=["POST"])
@jwt_required()
@admin_required
def set_document_structure(doc_id):
    """
    Définir la structure d'un document (admin uniquement)
    ---
    tags:
      - Documents
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: doc_id
        required: true
        schema:
          type: string
        description: ID du document
        example: "507f1f77bcf86cd799439060"
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - total_pages
            properties:
              total_pages:
                type: integer
                minimum: 1
                example: 150
                description: "Nombre total de pages du document"
              chapters:
                type: array
                description: "Chapitres du document"
                items:
                  type: object
                  properties:
                    chapter_id:
                      type: string
                      example: "ch1"
                    title:
                      type: string
                      example: "La Nouvelle Naissance"
                    start_page:
                      type: integer
                      example: 1
                    end_page:
                      type: integer
                      example: 15
                    page_count:
                      type: integer
                      example: 15
              sections:
                type: array
                description: "Sections détaillées pour les plans de lecture"
                items:
                  type: object
                  properties:
                    section_id:
                      type: string
                      example: "s1_1"
                    chapter_id:
                      type: string
                      example: "ch1"
                    title:
                      type: string
                      example: "Qu'est-ce que la nouvelle naissance?"
                    start_page:
                      type: integer
                      example: 1
                    end_page:
                      type: integer
                      example: 5
                    estimated_reading_time:
                      type: integer
                      example: 8
                      description: "Temps de lecture estimé en minutes"
    responses:
      200:
        description: Structure définie avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Structure mise à jour avec succès"
      400:
        description: Données invalides
        content:
          application/json:
            schema:
              type: object
              properties:
                errors:
                  type: object
                  description: "Erreurs de validation"
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis)
      404:
        description: Document non trouvé
      500:
        description: Erreur serveur
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
    ---
    tags:
      - Documents
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
          enum: [theology, devotional, study, biography, commentary]
        description: Filtrer par catégorie
        example: "devotional"
      - in: query
        name: language
        schema:
          type: string
          enum: [fr, en]
        description: Filtrer par langue
        example: "fr"
      - in: query
        name: has_page_numbers
        schema:
          type: boolean
        description: Filtrer les documents avec numérotation de pages
        example: true
      - in: query
        name: min_pages
        schema:
          type: integer
          minimum: 1
        description: Nombre minimum de pages
        example: 10
    responses:
      200:
        description: Documents récupérés avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Documents récupérés avec succès"
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
                        example: "La Marche Chrétienne"
                      author:
                        type: string
                        example: "Watchman Nee"
                      category:
                        type: string
                        enum: [theology, devotional, study, biography, commentary]
                        example: "devotional"
                      language:
                        type: string
                        enum: [fr, en]
                        example: "fr"
                      structure:
                        type: object
                        properties:
                          total_pages:
                            type: integer
                            example: 150
                          chapters:
                            type: array
                            items:
                              type: object
                          sections:
                            type: array
                            items:
                              type: object
                      reading_estimates:
                        type: object
                        properties:
                          fast:
                            type: string
                            example: "10 jours (15 pages/jour)"
                          normal:
                            type: string
                            example: "30 jours (5 pages/jour)"
                          slow:
                            type: string
                            example: "50 jours (3 pages/jour)"
                      stats:
                        type: object
                        properties:
                          download_count:
                            type: integer
                          view_count:
                            type: integer
                          plans_using:
                            type: integer
                      created_at:
                        type: string
                        format: date-time
                total:
                  type: integer
                  example: 25
                  description: "Nombre total de documents"
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
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
    ---
    tags:
      - Documents
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: doc_id
        required: true
        schema:
          type: string
        description: ID du document
        example: "507f1f77bcf86cd799439060"
    responses:
      200:
        description: Aide à la configuration récupérée avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Aide à la configuration récupérée avec succès"
                data:
                  type: object
                  properties:
                    document_info:
                      type: object
                      properties:
                        title:
                          type: string
                          example: "La Marche Chrétienne"
                        total_pages:
                          type: integer
                          example: 150
                        estimated_total_time:
                          type: integer
                          example: 300
                          description: "Temps de lecture total estimé en minutes"
                    suggestions:
                      type: object
                      properties:
                        daily_reading_options:
                          type: array
                          items:
                            type: object
                            properties:
                              type:
                                type: string
                                enum: [time_based, page_based]
                                example: "time_based"
                              daily_time:
                                type: integer
                                example: 15
                                description: "Temps quotidien en minutes (pour time_based)"
                              pages_per_day:
                                type: string
                                example: "~5 pages"
                                description: "Pages par jour (pour page_based)"
                              estimated_duration:
                                type: integer
                                example: 20
                                description: "Durée estimée en jours"
                        quick_templates:
                          type: array
                          items:
                            type: object
                            properties:
                              name:
                                type: string
                                example: "Lecture rapide (2 semaines)"
                              daily_commitment:
                                type: string
                                example: "20 minutes"
                              structure:
                                type: string
                                example: "~11 pages par jour"
      400:
        description: Document sans structure ou données invalides
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Structure du document non disponible"
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Document non trouvé
      500:
        description: Erreur serveur
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
    

@documents_bp.route("/church/<church_id>", methods=["GET"])
@jwt_required()
def get_church_documents(church_id):
    """
    Récupérer les documents d'une église spécifique
    ---
    tags:
      - Documents
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: church_id
        required: true
        schema:
          type: string
        description: ID de l'église
        example: "507f1f77bcf86cd799439050"
      - in: query
        name: category
        schema:
          type: string
          enum: [theology, devotional, study, biography, commentary]
        description: Filtrer par catégorie
        example: "devotional"
      - in: query
        name: language
        schema:
          type: string
          enum: [fr, en]
        description: Filtrer par langue
        example: "fr"
      - in: query
        name: has_structure
        schema:
          type: boolean
        description: Filtrer les documents avec structure définie
        example: true
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
      - in: query
        name: sort_by
        schema:
          type: string
          enum: [created_at, title, author, download_count]
          default: created_at
        description: Critère de tri
        example: "title"
    responses:
      200:
        description: Documents de l'église récupérés avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Documents de l'église récupérés avec succès"
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
                        example: "La Marche Chrétienne"
                      author:
                        type: string
                        example: "Watchman Nee"
                      category:
                        type: string
                        enum: [theology, devotional, study, biography, commentary]
                        example: "devotional"
                      language:
                        type: string
                        enum: [fr, en]
                        example: "fr"
                      description:
                        type: string
                        example: "Un guide pratique pour la vie chrétienne"
                      file_info:
                        type: object
                        properties:
                          original_filename:
                            type: string
                            example: "la_marche_chretienne.pdf"
                          file_path:
                            type: string
                            example: "/path/to/uploads/documents/la_marche_chretienne.pdf"
                            description: "Chemin absolu du fichier sur le serveur"
                          file_size:
                            type: integer
                            example: 2048576
                            description: "Taille du fichier en bytes"
                          upload_date:
                            type: string
                            format: date-time
                      absolute_file_path:
                        type: string
                        example: "/var/www/qbible/uploads/documents/la_marche_chretienne.pdf"
                        description: "Chemin absolu complet du fichier"
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé
      404:
        description: Église non trouvée
      500:
        description: Erreur serveur
    """
    try:
        # Vérification des permissions
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Vérifier si l'église existe
        church = mongo.db.churches.find_one({"_id": ObjectId(church_id)})
        if not church:
            return jsonify({"message": "Église non trouvée"}), 404
        
        # Vérifier les permissions d'accès
        user_church_id = str(user.get("church_id", ""))
        if user_church_id != church_id and user.get("role") not in ["admin", "super_admin"]:
            # L'utilisateur peut voir seulement les documents publics des autres églises
            access_filter = {"access.visibility": "public"}
        else:
            # L'utilisateur peut voir tous les documents de son église
            access_filter = {"access.visibility": {"$in": ["public", "church_only", "private"]}}
        
        # Préparer les filtres
        filters = {"access.church_id": ObjectId(church_id)}
        filters.update(access_filter)
        
        if request.args.get("category"):
            filters["category"] = request.args.get("category")
        if request.args.get("language"):
            filters["language"] = request.args.get("language")
        if request.args.get("has_structure"):
            has_structure = request.args.get("has_structure").lower() == 'true'
            if has_structure:
                filters["structure.total_pages"] = {"$gt": 0}
            else:
                filters["$or"] = [
                    {"structure.total_pages": {"$exists": False}},
                    {"structure.total_pages": 0}
                ]
        
        # Pagination
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        skip = (page - 1) * per_page
        
        # Tri
        sort_by = request.args.get("sort_by", "created_at")
        sort_field = "stats.download_count" if sort_by == "download_count" else sort_by
        sort_order = -1 if sort_by in ["created_at", "download_count"] else 1
        
        # Récupérer les documents
        documents = list(DocumentModel.get_collection().find(filters)
                        .sort(sort_field, sort_order)
                        .skip(skip)
                        .limit(per_page))
        
        # Compter le total
        total = DocumentModel.get_collection().count_documents(filters)
        
        # Convertir les ObjectId et ajouter le chemin absolu
        for doc in documents:
            doc["_id"] = str(doc["_id"])
            doc["access"]["uploaded_by"] = str(doc["access"]["uploaded_by"])
            if doc["access"].get("church_id"):
                doc["access"]["church_id"] = str(doc["access"]["church_id"])
            
            # Ajouter le chemin absolu du fichier
            if doc.get("file_info", {}).get("file_path"):
                doc["absolute_file_path"] = os.path.abspath(doc["file_info"]["file_path"])
            else:
                doc["absolute_file_path"] = None
        
        return jsonify({
            "message": "Documents de l'église récupérés avec succès",
            "data": documents,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
            "church_info": {
                "church_id": str(church["_id"]),
                "church_name": church.get("name", "")
            }
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

@documents_bp.route("/my-church", methods=["GET"])
@jwt_required()
def get_my_church_documents():
    """
    Lister les documents de mon église
    ---
    tags:
      - Documents
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
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
          maximum: 50
          default: 20
        description: Nombre d'éléments par page
        example: 20
    responses:
      200:
        description: Documents de votre église récupérés avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Documents de votre église récupérés avec succès"
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
                        example: "La Marche Chrétienne"
                      author:
                        type: string
                        example: "Watchman Nee"
                      category:
                        type: string
                        example: "study"
                      language:
                        type: string
                        example: "fr"
                      file_info:
                        type: object
                        properties:
                          original_filename:
                            type: string
                          file_size:
                            type: integer
                          upload_date:
                            type: string
                            format: date-time
                      absolute_file_path:
                        type: string
                        example: "/var/www/qbible/uploads/documents/file.pdf"
                      created_at:
                        type: string
                        format: date-time
                total:
                  type: integer
                  example: 25
                page:
                  type: integer
                  example: 1
                per_page:
                  type: integer
                  example: 20
                total_pages:
                  type: integer
                  example: 2
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Utilisateur sans église
      500:
        description: Erreur serveur
    """
    try:
        # Récupérer l'utilisateur depuis le JWT
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        if not user.get("church_id"):
            return jsonify({"message": "Utilisateur sans église"}), 404
        
        church_id = user["church_id"]
        
        # Filtre simple : seulement par église
        filters = {"access.church_id": ObjectId(church_id)}
        
        # Pagination
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        skip = (page - 1) * per_page
        
        # Récupérer les documents
        documents = list(DocumentModel.get_collection().find(filters)
                        .sort("created_at", -1)
                        .skip(skip)
                        .limit(per_page))
        
        total = DocumentModel.get_collection().count_documents(filters)
        
        # Convertir ObjectId et ajouter chemin absolu
        for doc in documents:
            doc["_id"] = str(doc["_id"])
            doc["access"]["uploaded_by"] = str(doc["access"]["uploaded_by"])
            doc["access"]["church_id"] = str(doc["access"]["church_id"])
            
            # Ajouter le chemin absolu
            if doc.get("file_info", {}).get("file_path"):
                doc["absolute_file_path"] = os.path.abspath(doc["file_info"]["file_path"])
            else:
                doc["absolute_file_path"] = None
        
        return jsonify({
            "message": "Documents de votre église récupérés avec succès",
            "data": documents,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500
 