from flask_jwt_extended import jwt_required
from flask import Blueprint, jsonify, request, send_file, current_app
from models.image_staff_model import ImageStaffModel
 
from services.church_service import (
    update_church_service,
    delete_church_service,
    get_all_church_service,
    toggle_church_status_service,
    get_church_service
)
import os
from datetime import datetime
 
from services.stats_staff_service import (
 
  get_utilisateurs_recents_connectes_service,
 
  ajouter_image_service
)
 
from utils.decorators import staff_required, role_required
from schemas.image_staff_schema import ImageStaffSchema
from marshmallow import ValidationError


# Activer ou désactiver un magasin
staff_bp = Blueprint('staff', __name__)
@staff_bp.route('/church/<church_id>', methods=['PATCH'])
@jwt_required()
@staff_required
def toggle_church(church_id):
    """
    Activer ou désactiver un church
    ---
    tags:
      - Churchs
    summary: Changer l'état d'activation d’une church (actif/inactif)
    description: >
      Cette route permet d’activer ou de désactiver un church existant.  
      Accessible uniquement au personnel disposant du rôle "staff".

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 
      - name: church_id
        in: path
        type: string
        required: true
        description: ID du church à activer ou désactiver
        example: "60a7c9cf1234567890abcdef"

    responses:
      200:
        description: Church activé ou désactivé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Church activé avec succès"
      404:
        description: Church non trouvé
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Church non trouvé"
      401:
        description: Non autorisé (JWT manquant ou invalide)
    """
    return toggle_church_status_service(church_id)



# Récupérer tous les magasins avec les utilisateurs associés
@staff_bp.route('/churchs', methods=['GET'])
@jwt_required()
@staff_required
def get_all_church():
    """
    Récupérer tous les churchs
    ---
    tags:
      - Churchs
    summary: Obtenir la liste de tous les churchs
    description: >
      Cette route permet de récupérer tous les churchs disponibles.  
      Accessible uniquement au personnel disposant du rôle "staff".

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 

    responses:
      200:
        description: Liste de tous les churchs récupérée avec succès
        schema:
          type: array
          items:
            type: object
            properties:
              _id:
                type: string
                example: "60a7c9cf1234567890abcdef"
              nom:
                type: string
                example: "church Central"
              actif:
                type: boolean
                example: true
              adresse:
                type: string
                example: "Douala, Bonamoussadi"
              created_at:
                type: string
                format: date-time
                example: "2025-07-10T14:30:00Z"
      401:
        description: Non autorisé (JWT manquant ou invalide)
    """
    return get_all_church_service()



 

# Récupérer un church par son ID
@staff_bp.route('/churchs/<church_id>', methods=['GET'])
@jwt_required()
@role_required("admin", "manager", "staff")
def get_church(church_id):
    """
    Récupérer un church par son ID
    ---
    tags:
      - Churchs
    summary: Détails d’un church spécifique
    description: Cette route permet aux utilisateurs autorisés (admin, manager, staff) de consulter un church via son identifiant.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 
      - name: church_id
        in: path
        type: string
        required: true
        description: ID du church à récupérer
        example: "60a7c9cf1234567890abcdef"

    responses:
      200:
        description: Détails du church récupérés avec succès
        schema:
          type: object
          properties:
            _id:
              type: string
              example: "60a7c9cf1234567890abcdef"
            nom:
              type: string
              example: "church Central"
            statut:
              type: string
              example: "actif"
            adresse:
              type: string
              example: "Quartier Commercial, Douala"
      404:
        description: church non trouvé
    """
    return get_church_service(church_id)
 

@staff_bp.route("/stats/utilisateurs-recents", methods=["GET"])
@jwt_required()
@role_required("staff")  
def get_utilisateurs_recents_connectes():
    """
    Récupérer les derniers utilisateurs connectés
    ---
    tags:
      - Statistiques
    summary: Derniers utilisateurs connectés
    description: >
      Cette route retourne les 10 derniers utilisateurs qui se sont connectés à la plateforme.
      Accessible uniquement aux membres du staff (Super Admin).
    
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 

    responses:
      200:
        description: Liste des derniers utilisateurs connectés
        schema:
          type: array
          items:
            type: object
            properties:
              user_id:
                type: string
                example: "60c72ef1532072e7c32ed48a"
              nom:
                type: string
                example: "Mfochivé"
              email:
                type: string
                example: "user@example.com"
              role:
                type: string
                example: "livreur"
              derniere_connexion:
                type: string
                format: date-time
                example: "2025-07-10T12:45:00Z"
      401:
        description: Non autorisé – Token invalide ou manquant
      500:
        description: Erreur serveur lors du traitement de la requête
    """
    try:
        data = get_utilisateurs_recents_connectes_service(limit=10)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"message": f"Erreur : {str(e)}"}), 500

    
  
@staff_bp.route("/churchs/export", methods=["GET"])
@jwt_required()
@role_required("admin", "staff")
def export_churchs_excel():
    """
    Exporter la liste des churchs au format Excel
    ---
    tags:
      - Export
    summary: Export des churchs
    description: Cette route permet d’exporter la liste complète des churchs enregistrés au format Excel (.xlsx). Le fichier est automatiquement généré et proposé au téléchargement.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Fichier Excel contenant la liste des churchs généré avec succès
        schema:
          type: file
      401:
        description: Non autorisé – Token manquant ou invalide
      500:
        description: Erreur lors de l’exportation des données ou du traitement serveur
    """
    result = get_all_church_service()

    if result.get("status") != 200:
        return {"error": result.get("message", "Erreur inconnue")}, 500

    churchs = result["churchs"]

    # Générer fichier Excel
    buffer = export_churchs_to_excel(churchs)

    # Enregistrer temporairement
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"churchs_{now}.xlsx"
    save_path = os.path.join(current_app.root_path, "exports")
    os.makedirs(save_path, exist_ok=True)
    full_path = os.path.join(save_path, filename)

    with open(full_path, "wb") as f:
        f.write(buffer.getvalue())

    # Télécharger
    return send_file(
        full_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )



@staff_bp.route("/images/upload", methods=["POST"])
@role_required("staff")
def upload_image():
    """
    Uploader une image sur la plateforme
    ---
    tags:
      - Upload
    summary: Upload d'image par un membre du staff
    description: Cette route permet à un membre du staff d'uploader une image vers la plateforme. Les champs `nom`, `description`, `categorie` et `tags` doivent être inclus dans le formulaire, ainsi que le fichier image.

    consumes:
      - multipart/form-data

    parameters:
      - name: nom
        in: formData
        type: string
        required: true
        description: Nom de l'image
      - name: description
        in: formData
        type: string
        required: false
        description: Description facultative de l'image
      - name: categorie
        in: formData
        type: string
        required: false
        description: Catégorie à laquelle appartient l'image
      - name: tags
        in: formData
        type: array
        items:
          type: string
        required: false
        description: Liste de tags associés à l'image (plusieurs valeurs possibles)
      - name: file
        in: formData
        type: file
        required: true
        description: Fichier image à uploader

    responses:
      200:
        description: Image uploadée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: Image enregistrée avec succès
            image_url:
              type: string
              example: https://domaine.com/uploads/image123.png
      400:
        description: Requête invalide – Fichier ou champs manquants/invalides
      401:
        description: Non autorisé – Accès réservé au personnel
      500:
        description: Erreur serveur lors du traitement
    """
    schema = ImageStaffSchema()
    try:
        data = schema.load(request.form)
    except ValidationError as err:
        return {"error": err.messages}, 400

    file = request.files.get("file")
    if not file:
        return {"error": "Fichier manquant"}, 400

    return ajouter_image_service(data, file)
 
 

@staff_bp.route("/images/by-category", methods=["GET"])
# @role_required("staff")
def get_images_by_category():
    """
    Liste les images groupées par catégorie
    ---
    tags:
      - Images Staff
    summary: Images groupées par catégorie
    description: Récupère toutes les images organisées par catégorie avec un résumé
    
    responses:
      200:
        description: Images groupées avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
            total:
              type: integer
              description: Nombre total d'images
              example: 15
            categories_count:
              type: integer
              description: Nombre de catégories
              example: 5
            summary:
              type: object
              description: Nombre d'images par catégorie
              example:
                branding: 3
                marketing: 5
                produits: 7
            categories:
              type: object
              description: Images groupées par catégorie
              additionalProperties:
                type: array
                items:
                  type: object
      401:
        description: Non autorisé
      500:
        description: Erreur serveur
    """
    result = get_images_by_category_service()
    return jsonify(result), result["status"]


@staff_bp.route("/images/<image_id>", methods=["DELETE"])
# @role_required("staff")
def delete_image(image_id):
    """
    Supprime une image
    ---
    tags:
      - Images Staff
    summary: Suppression d'une image
    description: Supprime une image de la base de données et du serveur
    
    parameters:
      - name: image_id
        in: path
        type: string
        required: true
        description: ID de l'image à supprimer
    
    responses:
      200:
        description: Image supprimée avec succès
      400:
        description: ID invalide
      404:
        description: Image non trouvée
      401:
        description: Non autorisé
      500:
        description: Erreur serveur
    """
    result = ImageStaffModel.supprimer_image(image_id)
    
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    
    return jsonify(result), 200