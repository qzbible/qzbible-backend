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

@documents_bp.route("/<doc_id>", methods=["GET"])
@jwt_required()
def get_document_by_id(doc_id):
    """
    Récupérer un document par son ID
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
        description: Document récupéré avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Document récupéré avec succès"
                data:
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
                          example: "la_marche_chretienne.pdf"
                        file_size:
                          type: integer
                          example: 2048576
                        upload_date:
                          type: string
                          format: date-time
                    structure:
                      type: object
                      properties:
                        total_pages:
                          type: integer
                          example: 150
                    access:
                      type: object
                      properties:
                        church_id:
                          type: string
                        uploaded_by:
                          type: string
                    absolute_file_path:
                      type: string
                      example: "/var/www/qbible/uploads/documents/file.pdf"
                    created_at:
                      type: string
                      format: date-time
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Document non trouvé
      500:
        description: Erreur serveur
    """
    try:
        # Récupérer le document
        document = DocumentModel.get_collection().find_one({"_id": ObjectId(doc_id)})
        
        if not document:
            return jsonify({"message": "Document non trouvé"}), 404
        
        # Convertir ObjectId et ajouter chemin absolu
        document["_id"] = str(document["_id"])
        document["access"]["uploaded_by"] = str(document["access"]["uploaded_by"])
        if document["access"].get("church_id"):
            document["access"]["church_id"] = str(document["access"]["church_id"])
        
        # Ajouter le chemin absolu
        if document.get("file_info", {}).get("file_path"):
            document["absolute_file_path"] = os.path.abspath(document["file_info"]["file_path"])
        else:
            document["absolute_file_path"] = None
        
        return jsonify({
            "message": "Document récupéré avec succès",
            "data": document
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
    

@documents_bp.route("/<doc_id>", methods=["DELETE"])
@jwt_required()
def delete_document(doc_id):
    """
    Supprimer définitivement un document
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
        description: ID du document à supprimer
        example: "507f1f77bcf86cd799439060"
    responses:
      200:
        description: Document supprimé avec succès
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Document supprimé avec succès"
                deleted_document_id:
                  type: string
                  example: "507f1f77bcf86cd799439060"
                file_deleted:
                  type: boolean
                  example: true
                  description: "Indique si le fichier physique a été supprimé"
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (pas le propriétaire du document)
      404:
        description: Document non trouvé
      500:
        description: Erreur serveur
    """
    try:
        # Récupérer l'utilisateur actuel
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Récupérer le document
        document = DocumentModel.get_collection().find_one({"_id": ObjectId(doc_id)})
        
        if not document:
            return jsonify({"message": "Document non trouvé"}), 404
        
        # Vérifier les permissions (seul l'uploader ou admin peut supprimer)
        can_delete = False
        
        # L'utilisateur qui a uploadé le document
        if str(document["access"]["uploaded_by"]) == current_user_id:
            can_delete = True
        
        # Admin de l'église
        if (user.get("role") in ["admin", "super_admin"] and 
            str(user.get("church_id", "")) == str(document["access"].get("church_id", ""))):
            can_delete = True
        
        if not can_delete:
            return jsonify({"message": "Accès refusé - vous ne pouvez pas supprimer ce document"}), 403
        
        # Récupérer le chemin du fichier avant suppression
        file_path = document.get("file_info", {}).get("file_path")
        file_deleted = False
        
        # Supprimer le fichier physique
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                file_deleted = True
            except Exception as file_error:
                # Log l'erreur mais continue la suppression de la DB
                print(f"Erreur lors de la suppression du fichier : {file_error}")
        
        # Supprimer le document de la base de données
        result = DocumentModel.get_collection().delete_one({"_id": ObjectId(doc_id)})
        
        if result.deleted_count == 0:
            return jsonify({"message": "Erreur lors de la suppression du document"}), 500
        
        return jsonify({
            "message": "Document supprimé avec succès",
            "deleted_document_id": doc_id,
            "file_deleted": file_deleted
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


 