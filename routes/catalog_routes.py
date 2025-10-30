# routes/catalog.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from schemas.catalog_schema import (
    PublishToCatalogSchema,
    CatalogFilterSchema,
    RateCatalogItemSchema,
    ImportFromCatalogSchema
)
from services.catalog_service import (
    publish_to_catalog_service,
    get_catalog_items_service,
    get_catalog_item_detail_service,
    import_from_catalog_service,
    rate_catalog_item_service,
    unpublish_from_catalog_service,
    get_my_published_content_service,
    get_catalog_stats_service,
    get_popular_tags_service,
    search_catalog_service
)
from utils.decorators import admin_required

catalog_bp = Blueprint("catalog", __name__, url_prefix="/api/catalog")


@catalog_bp.route("/browse", methods=["GET"])
@jwt_required()
def browse_catalog():
    """
    Parcourir le catalogue public
    ---
    tags:
      - Catalog
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: query
        name: content_type
        type: string
        required: false
        enum: [section, chapter, quiz]
        description: Filtrer par type de contenu
        example: "section"
      - in: query
        name: tags
        type: array
        items:
          type: string
        required: false
        description: Filtrer par tags (séparés par des virgules)
        example: "nouveau-converti,baptême"
      - in: query
        name: min_rating
        type: number
        required: false
        description: Note minimum (0-5)
        example: 4.0
      - in: query
        name: search
        type: string
        required: false
        description: Terme de recherche
        example: "foi"
      - in: query
        name: sort_by
        type: string
        required: false
        enum: [downloads, rating, recent]
        default: downloads
        description: Critère de tri
        example: "rating"
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
        description: Catalogue récupéré avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Catalogue récupéré avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "507f1f77bcf86cd799439060"
                  content_type:
                    type: string
                    enum: [section, chapter, quiz]
                    example: "section"
                  content_id:
                    type: string
                    example: "507f1f77bcf86cd799439011"
                  church_id:
                    type: string
                    example: "507f1f77bcf86cd799439012"
                  church_name:
                    type: string
                    example: "Église Source"
                  title:
                    type: string
                    example: "Formation Nouveau Converti"
                  description:
                    type: string
                  preview:
                    type: object
                    properties:
                      chapters_count:
                        type: integer
                        example: 5
                      quiz_count:
                        type: integer
                        example: 15
                      avg_rating:
                        type: number
                        example: 4.5
                  tags:
                    type: array
                    items:
                      type: string
                    example: ["nouveau-converti", "baptême"]
                  downloads_count:
                    type: integer
                    example: 45
                  rating:
                    type: number
                    example: 4.5
                  published_at:
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
        
        if request.args.get("content_type"):
            filters["content_type"] = request.args.get("content_type")
        
        if request.args.get("tags"):
            filters["tags"] = request.args.get("tags").split(",")
        
        if request.args.get("min_rating"):
            try:
                filters["min_rating"] = float(request.args.get("min_rating"))
            except:
                pass
        
        if request.args.get("search"):
            filters["search"] = request.args.get("search")
        
        if request.args.get("sort_by"):
            filters["sort_by"] = request.args.get("sort_by")
        
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        
        result = get_catalog_items_service(filters if filters else None, page, per_page)
        
        return jsonify({
            "message": "Catalogue récupéré avec succès",
            **result
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@catalog_bp.route("/item/<catalog_item_id>", methods=["GET"])
@jwt_required()
def get_catalog_item(catalog_item_id):
    """
    Récupérer les détails d'un élément du catalogue
    ---
    tags:
      - Catalog
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: path
        name: catalog_item_id
        type: string
        required: true
        description: ID de l'élément du catalogue
        example: "507f1f77bcf86cd799439060"
    responses:
      200:
        description: Détails de l'élément récupérés avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Détails récupérés avec succès"
            data:
              type: object
              properties:
                _id:
                  type: string
                content_type:
                  type: string
                content_id:
                  type: string
                church_id:
                  type: string
                church_name:
                  type: string
                title:
                  type: string
                description:
                  type: string
                preview:
                  type: object
                tags:
                  type: array
                  items:
                    type: string
                downloads_count:
                  type: integer
                rating:
                  type: number
                ratings_count:
                  type: integer
                published_at:
                  type: string
                  format: date-time
                recent_ratings:
                  type: array
                  description: 5 avis les plus récents
                  items:
                    type: object
                    properties:
                      _id:
                        type: string
                      user_id:
                        type: string
                      rating:
                        type: number
                      comment:
                        type: string
                      created_at:
                        type: string
                        format: date-time
                user_rating:
                  type: object
                  description: Note de l'utilisateur connecté (si existe)
                  properties:
                    rating:
                      type: number
                    comment:
                      type: string
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Élément non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        
        item = get_catalog_item_detail_service(catalog_item_id, current_user_id)
        
        if isinstance(item, tuple):
            return jsonify(item[0]), item[1]
        
        return jsonify({
            "message": "Détails récupérés avec succès",
            "data": item
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@catalog_bp.route("/publish", methods=["POST"])
@jwt_required()
@admin_required
def publish_to_catalog():
    """
    Publier du contenu au catalogue public (admin uniquement)
    ---
    tags:
      - Catalog
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
        description: Contenu à publier
        schema:
          type: object
          required:
            - content_type
            - content_id
          properties:
            content_type:
              type: string
              enum: [section, chapter, quiz]
              example: "section"
              description: Type de contenu à publier
            content_id:
              type: string
              example: "507f1f77bcf86cd799439011"
              description: ID du contenu à publier
            tags:
              type: array
              items:
                type: string
              example: ["nouveau-converti", "baptême", "fondamentaux"]
              description: Tags pour faciliter la recherche (max 10)
    responses:
      201:
        description: Contenu publié au catalogue avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Contenu publié au catalogue avec succès"
            catalog_item_id:
              type: string
              example: "507f1f77bcf86cd799439060"
      400:
        description: Données invalides ou contenu déjà publié
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Ce contenu est déjà publié au catalogue"
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis)
      404:
        description: Contenu non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Valider
        errors = PublishToCatalogSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = publish_to_catalog_service(
            data["content_type"],
            data["content_id"],
            str(user["church_id"]),
            data.get("tags", [])
        )
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@catalog_bp.route("/import", methods=["POST"])
@jwt_required()
@admin_required
def import_from_catalog():
    """
    Importer du contenu depuis le catalogue (admin uniquement)
    ---
    tags:
      - Catalog
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
        description: Élément à importer
        schema:
          type: object
          required:
            - catalog_item_id
          properties:
            catalog_item_id:
              type: string
              example: "507f1f77bcf86cd799439060"
              description: ID de l'élément du catalogue à importer
            target_section_id:
              type: string
              example: "507f1f77bcf86cd799439011"
              description: ID de la section cible (requis pour chapitre/quiz)
    responses:
      201:
        description: Contenu importé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Contenu importé avec succès"
            content_type:
              type: string
              example: "section"
            new_content_id:
              type: string
              example: "507f1f77bcf86cd799439070"
              description: ID du nouveau contenu créé dans votre église
            already_downloaded:
              type: boolean
              example: false
              description: Indique si ce contenu avait déjà été téléchargé
      400:
        description: Données invalides
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis)
      404:
        description: Élément du catalogue non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Valider
        errors = ImportFromCatalogSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = import_from_catalog_service(
            data["catalog_item_id"],
            str(user["church_id"]),
            current_user_id,
            data.get("target_section_id")
        )
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@catalog_bp.route("/rate", methods=["POST"])
@jwt_required()
def rate_catalog_item():
    """
    Noter un élément du catalogue
    ---
    tags:
      - Catalog
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
        description: Note et avis
        schema:
          type: object
          required:
            - catalog_item_id
            - rating
          properties:
            catalog_item_id:
              type: string
              example: "507f1f77bcf86cd799439060"
              description: ID de l'élément à noter
            rating:
              type: number
              minimum: 1
              maximum: 5
              example: 4.5
              description: Note de 1 à 5
            comment:
              type: string
              maxLength: 500
              example: "Excellente ressource pour les nouveaux convertis !"
              description: Commentaire optionnel (max 500 caractères)
    responses:
      200:
        description: Note ajoutée ou mise à jour avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Note ajoutée avec succès"
            rating_id:
              type: string
              example: "507f1f77bcf86cd799439061"
            updated:
              type: boolean
              example: false
              description: true si la note existante a été mise à jour
      400:
        description: Données invalides
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Élément du catalogue non trouvé
      500:
        description: Erreur serveur
    """
    try:
        data = request.get_json()
        
        # Ajouter catalog_item_id au niveau racine pour validation
        if "catalog_item_id" not in data:
            return jsonify({"message": "catalog_item_id est requis"}), 400
        
        # Valider
        errors = RateCatalogItemSchema().validate({
            "rating": data.get("rating"),
            "comment": data.get("comment")
        })
        if errors:
            return jsonify({"errors": errors}), 400
        
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = rate_catalog_item_service(
            data["catalog_item_id"],
            current_user_id,
            str(user["church_id"]),
            data["rating"],
            data.get("comment")
        )
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@catalog_bp.route("/unpublish/<catalog_item_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def unpublish_from_catalog(catalog_item_id):
    """
    Retirer un contenu du catalogue (admin uniquement)
    ---
    tags:
      - Catalog
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur (admin requis)
        example: "Bearer votre.jwt.token"
      - in: path
        name: catalog_item_id
        type: string
        required: true
        description: ID de l'élément à retirer du catalogue
        example: "507f1f77bcf86cd799439060"
    responses:
      200:
        description: Contenu retiré du catalogue avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Contenu retiré du catalogue avec succès"
            deleted_count:
              type: integer
              example: 1
      401:
        description: Token JWT manquant ou invalide
      403:
        description: Accès refusé (admin requis ou contenu d'une autre église)
      404:
        description: Élément non trouvé
      500:
        description: Erreur serveur
    """
    try:
        current_user_id = get_jwt_identity()
        from extensions import mongo
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        result, status = unpublish_from_catalog_service(catalog_item_id, str(user["church_id"]))
        
        return jsonify(result), status
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@catalog_bp.route("/my-published", methods=["GET"])
@jwt_required()
@admin_required
def get_my_published():
    """
    Récupérer le contenu publié par mon église (admin uniquement)
    ---
    tags:
      - Catalog
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
        description: Contenu publié récupéré avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Votre contenu publié récupéré avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                  content_type:
                    type: string
                  content_id:
                    type: string
                  title:
                    type: string
                  downloads_count:
                    type: integer
                  rating:
                    type: number
                  published_at:
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
        
        items = get_my_published_content_service(str(user["church_id"]))
        
        return jsonify({
            "message": "Votre contenu publié récupéré avec succès",
            "data": items,
            "total": len(items)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@catalog_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_catalog_stats():
    """
    Récupérer les statistiques du catalogue
    ---
    tags:
      - Catalog
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
                total_items:
                  type: integer
                  example: 150
                  description: Nombre total d'éléments dans le catalogue
                total_downloads:
                  type: integer
                  example: 2450
                  description: Nombre total de téléchargements
                by_type:
                  type: array
                  description: Statistiques par type de contenu
                  items:
                    type: object
                    properties:
                      _id:
                        type: string
                        example: "section"
                      count:
                        type: integer
                        example: 45
                      total_downloads:
                        type: integer
                        example: 1200
                      avg_rating:
                        type: number
                        example: 4.3
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        stats = get_catalog_stats_service()
        
        return jsonify({
            "message": "Statistiques récupérées avec succès",
            "data": stats
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@catalog_bp.route("/tags", methods=["GET"])
@jwt_required()
def get_popular_tags():
    """
    Récupérer les tags les plus populaires
    ---
    tags:
      - Catalog
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: query
        name: limit
        type: integer
        required: false
        default: 20
        description: Nombre maximum de tags à retourner
        example: 20
    responses:
      200:
        description: Tags récupérés avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Tags populaires récupérés avec succès"
            data:
              type: array
              items:
                type: object
                properties:
                  tag:
                    type: string
                    example: "nouveau-converti"
                  count:
                    type: integer
                    example: 25
                    description: Nombre d'éléments avec ce tag
            total:
              type: integer
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
    """
    try:
        limit = int(request.args.get("limit", 20))
        tags = get_popular_tags_service(limit)
        
        return jsonify({
            "message": "Tags populaires récupérés avec succès",
            "data": tags,
            "total": len(tags)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500


@catalog_bp.route("/search", methods=["GET"])
@jwt_required()
def search_catalog():
    """
    Rechercher dans le catalogue
    ---
    tags:
      - Catalog
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
        type: string
        required: true
        description: Terme de recherche
        example: "baptême"
    responses:
      200:
        description: Résultats de recherche récupérés avec succès
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
                description: Éléments du catalogue correspondants
            total:
              type: integer
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
        
        items = search_catalog_service(search_term)
        
        return jsonify({
            "message": "Résultats de recherche récupérés avec succès",
            "data": items,
            "total": len(items)
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500