from flask_jwt_extended import jwt_required
from flask import Blueprint, jsonify, request, send_file, current_app
from models.image_staff_model import ImageStaffModel
from services.magasin_service import (
    update_magasin_service,
    delete_magasin_service,
    get_all_magasin_service,
    toggle_magasin_status_service,
    get_magasin_service
)
import os
from datetime import datetime
from services.export_files_services import export_magasins_to_excel
from services.stats_staff_service import (
  get_all_images_service,
  get_image_by_id_service,
  get_stats_utilisation_globale,
  get_utilisateurs_recents_connectes_service,
  get_top_magasin_par_chiffre_affaire,
  get_nombre_magasins_total,
  get_nombre_admins_managers_total,
  get_nombre_livreurs_total,
  get_nombre_clients_total,
  ajouter_image_service
)
from schemas.magasin_schema import MagasinUpdateSchema
from utils.decorators import staff_required, role_required
from schemas.image_staff_schema import ImageStaffSchema
from marshmallow import ValidationError





# Activer ou désactiver un magasin
staff_bp = Blueprint('staff', __name__)
@staff_bp.route('/magasins/<magasin_id>', methods=['PATCH'])
@jwt_required()
@staff_required
def toggle_magasin(magasin_id):
    """
    Activer ou désactiver un magasin
    ---
    tags:
      - Magasins
    summary: Changer l'état d'activation d’un magasin (actif/inactif)
    description: >
      Cette route permet d’activer ou de désactiver un magasin existant.  
      Accessible uniquement au personnel disposant du rôle "staff".

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 
      - name: magasin_id
        in: path
        type: string
        required: true
        description: ID du magasin à activer ou désactiver
        example: "60a7c9cf1234567890abcdef"

    responses:
      200:
        description: Magasin activé ou désactivé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Magasin activé avec succès"
      404:
        description: Magasin non trouvé
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Magasin non trouvé"
      401:
        description: Non autorisé (JWT manquant ou invalide)
    """
    return toggle_magasin_status_service(magasin_id)



# Récupérer tous les magasins avec les utilisateurs associés
@staff_bp.route('/magasins', methods=['GET'])
@jwt_required()
@staff_required
def get_all_magasin():
    """
    Récupérer tous les magasins
    ---
    tags:
      - Magasins
    summary: Obtenir la liste de tous les magasins
    description: >
      Cette route permet de récupérer tous les magasins disponibles.  
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
        description: Liste de tous les magasins récupérée avec succès
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
                example: "Magasin Central"
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
    return get_all_magasin_service()






# Supprimer un magasin
@staff_bp.route('/magasins/<magasin_id>', methods=['DELETE'])
@jwt_required()
@role_required("staff")
def delete_magasin(magasin_id):
    """
    Supprimer un magasin
    ---
    tags:
      - Magasins
    summary: Suppression d’un magasin par ID
    description: >
      Cette route permet à un membre du staff de supprimer un magasin à partir de son identifiant.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 
      - name: magasin_id
        in: path
        type: string
        required: true
        description: ID du magasin à supprimer
        example: "60a7c9cf1234567890abcdef"

    responses:
      200:
        description: Magasin supprimé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Magasin supprimé avec succès"
      404:
        description: Magasin non trouvé
    """
    return delete_magasin_service(magasin_id)


# Récupérer un magasin par son ID
@staff_bp.route('/magasins/<magasin_id>', methods=['GET'])
@jwt_required()
@role_required("admin", "manager", "staff")
def get_magasin(magasin_id):
    """
    Récupérer un magasin par son ID
    ---
    tags:
      - Magasins
    summary: Détails d’un magasin spécifique
    description: Cette route permet aux utilisateurs autorisés (admin, manager, staff) de consulter un magasin via son identifiant.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 
      - name: magasin_id
        in: path
        type: string
        required: true
        description: ID du magasin à récupérer
        example: "60a7c9cf1234567890abcdef"

    responses:
      200:
        description: Détails du magasin récupérés avec succès
        schema:
          type: object
          properties:
            _id:
              type: string
              example: "60a7c9cf1234567890abcdef"
            nom:
              type: string
              example: "Magasin Central"
            statut:
              type: string
              example: "actif"
            adresse:
              type: string
              example: "Quartier Commercial, Douala"
      404:
        description: Magasin non trouvé
    """
    return get_magasin_service(magasin_id)

  
  
# Récupérer les statistiques d'utilisation de la plateforme
@staff_bp.route("/stats/utilisation", methods=["GET"])
@jwt_required()
@role_required("staff")  
def get_stats_utilisation():
    """
    Obtenir les statistiques globales d'utilisation de la plateforme
    ---
    tags:
      - Statistiques
    summary: Statistiques globales de la plateforme
    description: >
      Cette route retourne des données statistiques globales sur l’utilisation
      de la plateforme avec possibilité d’agrégation par jour, semaine, mois ou année.
      La pagination est également disponible via le paramètre `page`.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 
      - name: granularite
        in: query
        type: string
        required: false
        enum: [jour, semaine, mois, annee]
        description: Granularité d’agrégation des statistiques
        example: "semaine"
      - name: page
        in: query
        type: integer
        required: false
        description: Numéro de la page (0 = période actuelle, -1 = période précédente, etc.)
        example: 0

    responses:
      200:
        description: Statistiques récupérées avec succès
        schema:
          type: object
          properties:
            periode:
              type: string
              example: "2025-S27"
            total_commandes:
              type: integer
              example: 145
            total_utilisateurs:
              type: integer
              example: 25
            revenu_total:
              type: number
              format: float
              example: 542500.0
      400:
        description: Requête invalide (paramètre incorrect)
      401:
        description: Non autorisé – Token manquant ou invalide
      500:
        description: Erreur serveur lors du traitement de la requête
    """
    granularite = request.args.get("granularite", "semaine")
    page = int(request.args.get("page", 0))
    return get_stats_utilisation_globale(granularite, page)




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

      
@staff_bp.route("/stats/top-magasins", methods=["GET"])
@jwt_required()
@role_required("staff")
def get_top_magasins():
    """
    Obtenir les meilleurs magasins selon le chiffre d’affaires
    ---
    tags:
      - Statistiques
    summary: Top magasins par chiffre d’affaires
    description: >
      Cette route retourne les 5 meilleurs magasins classés par chiffre d'affaires global.
      Accessible uniquement aux membres du staff.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 

    responses:
      200:
        description: Liste des meilleurs magasins
        schema:
          type: array
          items:
            type: object
            properties:
              magasin_id:
                type: string
                example: "60c72ef1532072e7c32ed48a"
              nom:
                type: string
                example: "Magasin Central"
              chiffre_affaire:
                type: number
                format: float
                example: 129000.75
      401:
        description: Non autorisé – Token manquant ou invalide
      500:
        description: Erreur serveur lors du traitement de la requête
    """
    try:
        data = get_top_magasin_par_chiffre_affaire(limit=5)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"message": f"Erreur : {str(e)}"}), 500



# nombre de magasin totals
@staff_bp.route("/magasins/total", methods=["GET"])
@jwt_required()
@role_required("admin", "manager", "staff")
def route_nombre_magasins_total():
    """
    Récupérer le nombre total de magasins
    ---
    tags:
      - Statistiques
    summary: Nombre total de magasins enregistrés
    description: Cette route retourne le nombre total de magasins dans le système.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 

    responses:
      200:
        description: Nombre total de magasins récupéré avec succès
        schema:
          type: object
          properties:
            total_magasins:
              type: integer
              example: 42
      401:
        description: Non autorisé – Token manquant ou invalide
      500:
        description: Erreur serveur lors du traitement
    """
    result = get_nombre_magasins_total()
    return jsonify(result)

  
  
# nombre d'admin ou de manager totals pour toute la plateforme
@staff_bp.route("/admins-managers/total", methods=["GET"])
@jwt_required()
@role_required("admin", "manager", "staff")
def route_nombre_admins_managers_total():
    """
    Récupérer le nombre total d'administrateurs et de managers
    ---
    tags:
      - Statistiques
    summary: Nombre total d'admins et de managers enregistrés
    description: Cette route retourne le nombre total d'utilisateurs ayant le rôle "admin" ou "manager" dans le système.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 

    responses:
      200:
        description: Nombre total d'admins et de managers récupéré avec succès
        schema:
          type: object
          properties:
            total_admins_managers:
              type: integer
              example: 17
      401:
        description: Non autorisé – Token manquant ou invalide
      500:
        description: Erreur serveur lors du traitement
    """
    result = get_nombre_admins_managers_total()
    return jsonify(result)

  
  
@staff_bp.route("/livreurs/total", methods=["GET"])
@jwt_required()
@role_required("admin", "manager", "staff")
def route_nombre_livreurs_total():
    """
    Récupérer le nombre total de livreurs
    ---
    tags:
      - Statistiques
    summary: Nombre total de livreurs enregistrés
    description: Cette route retourne le nombre total de livreurs enregistrés sur toute la plateforme.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 

    responses:
      200:
        description: Nombre total de livreurs récupéré avec succès
        schema:
          type: object
          properties:
            total_livreurs:
              type: integer
              example: 25
      401:
        description: Non autorisé – Token manquant ou invalide
      500:
        description: Erreur serveur lors du traitement
    """
    result = get_nombre_livreurs_total()
    return jsonify(result)

  
# nombre de client  totals pour toute la plateforme
@staff_bp.route("/clients/total", methods=["GET"])
@jwt_required()
@role_required("admin", "manager", "staff")
def route_nombre_clients_total():
    """
    Récupérer le nombre total de clients
    ---
    tags:
      - Statistiques
    summary: Nombre total de clients enregistrés
    description: Cette route retourne le nombre total de clients enregistrés sur la plateforme.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer 

    responses:
      200:
        description: Nombre total de clients récupéré avec succès
        schema:
          type: object
          properties:
            total_clients:
              type: integer
              example: 150
      401:
        description: Non autorisé – Token manquant ou invalide
      500:
        description: Erreur serveur lors du traitement
    """
    result = get_nombre_clients_total()
    return jsonify(result)

  
  
@staff_bp.route("/magasins/export", methods=["GET"])
@jwt_required()
@role_required("admin", "staff")
def export_magasins_excel():
    """
    Exporter la liste des magasins au format Excel
    ---
    tags:
      - Export
    summary: Export des magasins
    description: Cette route permet d’exporter la liste complète des magasins enregistrés au format Excel (.xlsx). Le fichier est automatiquement généré et proposé au téléchargement.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Fichier Excel contenant la liste des magasins généré avec succès
        schema:
          type: file
      401:
        description: Non autorisé – Token manquant ou invalide
      500:
        description: Erreur lors de l’exportation des données ou du traitement serveur
    """
    result = get_all_magasin_service()

    if result.get("status") != 200:
        return {"error": result.get("message", "Erreur inconnue")}, 500

    magasins = result["magasins"]

    # Générer fichier Excel
    buffer = export_magasins_to_excel(magasins)

    # Enregistrer temporairement
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"magasins_{now}.xlsx"
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



@staff_bp.route("/images", methods=["GET"])
# @role_required("staff")
def get_all_images():
    """
    Liste toutes les images
    ---
    tags:
      - Images Staff
    summary: Liste toutes les images uploadées par le staff
    description: Récupère toutes les images avec leurs URLs complètes
    
    responses:
      200:
        description: Liste des images récupérée avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            count:
              type: integer
              example: 15
            images:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "60d5ec49f1b2c8a9e4f3b1a2"
                  nom:
                    type: string
                    example: "Logo Entreprise"
                  description:
                    type: string
                    example: "Logo principal"
                  categorie:
                    type: string
                    example: "branding"
                  filename:
                    type: string
                    example: "logo.png"
                  url:
                    type: string
                    example: "http://localhost:5000/uploads/staff_images/logo.png"
                  tags:
                    type: array
                    items:
                      type: string
                    example: ["logo", "officiel"]
                  created_at:
                    type: string
                    format: date-time
      401:
        description: Non autorisé
      500:
        description: Erreur serveur
    """
    result = get_all_images_service()
    return jsonify(result), result["status"]


@staff_bp.route("/images/<image_id>", methods=["GET"])
# @role_required("staff")
def get_image_by_id(image_id):
    """
    Récupère une image par son ID
    ---
    tags:
      - Images Staff
    summary: Détails d'une image
    description: Récupère les informations complètes d'une image spécifique
    
    parameters:
      - name: image_id
        in: path
        type: string
        required: true
        description: ID de l'image
        example: "60d5ec49f1b2c8a9e4f3b1a2"
    
    responses:
      200:
        description: Image trouvée
        schema:
          type: object
          properties:
            success:
              type: boolean
            image:
              type: object
      400:
        description: ID invalide
      404:
        description: Image non trouvée
      401:
        description: Non autorisé
      500:
        description: Erreur serveur
    """
    result = get_image_by_id_service(image_id)
    return jsonify(result), result["status"]


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