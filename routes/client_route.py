from flask import Blueprint, request, jsonify, send_file, current_app
from schemas.client_schema import CreateClientSchema, UpdateClientSchema
from utils.inject_magasin_id import inject_magasin_id
from utils.decorators import role_required
from datetime import datetime
import os
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.export_files_services import export_clients_to_excel
from services.client_service import (
    create_client_service,
    get_all_clients_service,
    get_client_by_id_service,
    update_client_service,
    delete_client_service,
    get_clients_livreur,
    get_meilleurs_clients_livreur,
    get_meilleurs_clients_total,
    get_clients_magasins
)
from models.user_model import UserModel


client_bp = Blueprint("client", __name__, url_prefix="/clients")


@client_bp.route("/create", methods=["POST"])
@jwt_required()
@role_required("admin", "manager", "livreur")
def create_client():
    """
    Créer un nouveau client
    ---
    tags:
      - Clients
    summary: Création d'un nouveau client
    description: Cette route permet aux utilisateurs autorisés (admin, manager, livreur) de créer un nouveau client en fournissant les informations requises via un formulaire.

    consumes:
      - multipart/form-data

    parameters:
      - in: formData
        name: nom
        type: string
        required: true
        description: Nom complet du client (au moins 2 caractères)
      - in: formData
        name: telephone
        type: string
        required: true
        description: Numéro de téléphone du client (au moins 8 chiffres)
      - in: formData
        name: email
        type: string
        required: false
        description: Adresse email du client (optionnelle)
      - in: formData
        name: ville
        type: string
        required: true
        description: Ville du client
      - in: formData
        name: quartier
        type: string
        required: true
        description: Quartier ou zone de résidence
      - in: formData
        name: magasin_id
        type: string
        required: true
        description: ID du magasin associé au client
      - in: formData
        name: photo_profil
        type: file
        required: false
        description: Photo de profil du client (format image)

    responses:
      201:
        description: Client créé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: Client créé avec succès
            client_id:
              type: string
              example: 64b8fae5e3b9ab9c8dbf8f67
      400:
        description: Données invalides (champs requis manquants ou mal formatés)
      401:
        description: Non autorisé – Jeton JWT manquant ou invalide
      500:
        description: Erreur interne lors de la création du client
    """
    data = dict(request.form)
    data = inject_magasin_id(data)
    created_by = get_jwt_identity()
    data["created_by"] = created_by  # Ajoute l'ID de l'utilisateur qui crée le client
    file = request.files.get("photo_profil")
    errors = CreateClientSchema().validate(data)
    if errors:
        return jsonify({"errors": errors}), 400
    return create_client_service(data, photo_file=file)



@client_bp.route("/", methods=["GET"])
@jwt_required()
@role_required("admin", "manager", "livreur", "staff")
def get_clients():
    """
    Récupérer la liste de tous les clients
    ---
    tags:
      - Clients
    summary: Obtenir la liste des clients
    description: Cette route permet de récupérer la liste de tous les clients associés à un magasin spécifique selon les droits de l'utilisateur connecté.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Liste des clients récupérée avec succès
        schema:
          type: object
          properties:
            clients:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    example: "64b8fae5e3b9ab9c8dbf8f67"
                  nom:
                    type: string
                    example: "Jean Dupont"
                  telephone:
                    type: string
                    example: "+237690123456"
                  email:
                    type: string
                    example: "jean@example.com"
                  ville:
                    type: string
                    example: "Yaoundé"
                  quartier:
                    type: string
                    example: "Bastos"
                  magasin_id:
                    type: string
                    example: "62de123abc12e123de123abc"
      401:
        description: Non autorisé – Jeton manquant ou invalide
      500:
        description: Erreur interne lors de la récupération des clients
    """
    data = {}
    data = inject_magasin_id(data)
    magasin_id = data.get("magasin_id")
    result = get_all_clients_service(magasin_id)
    return jsonify(result), 200



@client_bp.route("/<client_id>", methods=["GET"])
@jwt_required() 
@role_required("admin", "manager", "livreur", "staff")
def get_client(client_id):
    """
    Récupérer un client par ID
    ---
    tags:
      - Clients
    summary: Détails d’un client
    description: Cette route permet de récupérer les informations détaillées d’un client à partir de son identifiant unique.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer
      - in: path
        name: client_id
        type: string
        required: true
        description: ID unique du client à récupérer

    responses:
      200:
        description: Détails du client récupérés avec succès
        schema:
          type: object
          properties:
            id:
              type: string
              example: "64b8fae5e3b9ab9c8dbf8f67"
            nom:
              type: string
              example: "Jean Dupont"
            telephone:
              type: string
              example: "+237690123456"
            email:
              type: string
              example: "jean@example.com"
            ville:
              type: string
              example: "Douala"
            quartier:
              type: string
              example: "Akwa"
            magasin_id:
              type: string
              example: "62de123abc12e123de123abc"
      404:
        description: Client non trouvé
      401:
        description: Non autorisé – Jeton manquant ou invalide
      500:
        description: Erreur interne lors de la récupération du client
    """
    client = get_client_by_id_service(client_id)
    if not client:
        return jsonify({"error": "Client non trouvé"}), 404
    return jsonify(client), 200



#Mettre à jour un client

@client_bp.route("/<client_id>", methods=["PUT"])
@jwt_required()
@role_required("admin", "manager", "livreur")
def update_client(client_id):
    """
    Mettre à jour les informations d’un client
    ---
    tags:
      - Clients
    summary: Modification d’un client
    description: Cette route permet de mettre à jour les informations d’un client existant. Seuls les champs envoyés seront modifiés.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer
      - in: path
        name: client_id
        type: string
        required: true
        description: Identifiant unique du client à mettre à jour
      - in: body
        name: body
        required: true
        description: Champs à mettre à jour (un ou plusieurs)
        schema:
          type: object
          properties:
            nom:
              type: string
              example: "Jean Paul"
            telephone:
              type: string
              example: "+237699123456"
            email:
              type: string
              example: "jean.paul@example.com"
            ville:
              type: string
              example: "Yaoundé"
            quartier:
              type: string
              example: "Nlongkak"

    responses:
      200:
        description: Client mis à jour avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: Client mis à jour
      400:
        description: Données invalides
      401:
        description: Non autorisé – Jeton manquant ou invalide
      404:
        description: Client non trouvé
      500:
        description: Erreur interne lors de la mise à jour
    """
    data = request.get_json()
    errors = UpdateClientSchema().validate(data)
    if errors:
        return jsonify({"errors": errors}), 400
    update_client_service(client_id, data)
    return jsonify({"message": "Client mis à jour"}), 200


# Supprimer un client par ID

@client_bp.route("/<client_id>", methods=["DELETE"])
@role_required("admin", "manager", "livreur", "staff")
@jwt_required()
def delete_client(client_id):
    """
    Supprimer un client par ID
    ---
    tags:
      - Clients
    summary: Suppression d’un client
    description: Cette route permet de supprimer un client existant à partir de son identifiant unique. L’opération est réservée aux utilisateurs autorisés.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer
      - in: path
        name: client_id
        type: string
        required: true
        description: Identifiant unique du client à supprimer

    responses:
      200:
        description: Client supprimé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: Client supprimé
      401:
        description: Non autorisé – Jeton manquant ou invalide
      404:
        description: Client non trouvé
      500:
        description: Erreur serveur lors de la suppression
    """
    delete_client_service(client_id)
    return jsonify({"message": "Client supprimé"}), 200

  
# Récupérer tous les clients d'un livreur avec le nombre de livraisons et le montant total

@client_bp.route("/livreur/", methods=["GET"])
@jwt_required()
@role_required("livreur")
def recuperer_clients_livreur():
    """
    Récupérer les clients d’un livreur avec statistiques
    ---
    tags:
      - Clients
    summary: Liste des clients assignés à un livreur
    description: Cette route retourne la liste des clients associés au livreur connecté, avec le nombre total de livraisons et le montant total généré pour chaque client.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT du livreur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Liste des clients récupérée avec succès
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
                example: "64b8fae5e3b9ab9c8dbf8f67"
              nom:
                type: string
                example: "Marie Mbarga"
              telephone:
                type: string
                example: "+237690112233"
              ville:
                type: string
                example: "Douala"
              quartier:
                type: string
                example: "Bonamoussadi"
              nombre_livraisons:
                type: integer
                example: 12
              montant_total:
                type: number
                format: float
                example: 258000.0
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé
      500:
        description: Erreur serveur lors de la récupération
    """
    current_user_id = get_jwt_identity()
    clients = get_clients_livreur(current_user_id)
    return jsonify(clients), 200

  

@client_bp.route("/manager/", methods=["GET"])
@jwt_required()
@role_required("manager", "admin")
def recuperer_clients_magasin():
    """
    Récupérer les clients du magasin avec filtres dynamiques
    ---
    tags:
      - Clients
    summary: Recherche des clients du magasin avec filtres
    description: Cette route permet aux managers et admins de récupérer la liste des clients d’un magasin en appliquant des filtres dynamiques sur plusieurs champs.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer
      - name: nom
        in: query
        type: string
        required: false
        description: Filtrer par nom du client (recherche partielle possible)
      - name: telephone
        in: query
        type: string
        required: false
        description: Filtrer par numéro de téléphone
      - name: quartier
        in: query
        type: string
        required: false
        description: Filtrer par quartier
      - name: ville
        in: query
        type: string
        required: false
        description: Filtrer par ville
      - name: created_by_name
        in: query
        type: string
        required: false
        description: Filtrer par nom de la personne ayant créé le client

    responses:
      200:
        description: Liste filtrée des clients récupérée avec succès
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
                example: "64b8fae5e3b9ab9c8dbf8f67"
              nom:
                type: string
                example: "Pauline Ngono"
              telephone:
                type: string
                example: "+237699887766"
              ville:
                type: string
                example: "Yaoundé"
              quartier:
                type: string
                example: "Nkolndongo"
              created_by_name:
                type: string
                example: "Manager Jean"
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé
      500:
        description: Erreur serveur lors de la récupération des clients
    """
    filters = {
        "nom": request.args.get("nom"),
        "telephone": request.args.get("telephone"),
        "quartier": request.args.get("quartier"),
        "ville": request.args.get("ville"),
        "created_by_name": request.args.get("created_by_name"),
    }

    clients = get_clients_magasins(filters)
    return jsonify(clients), 200



@client_bp.route("/manager/export", methods=["GET"])
@jwt_required()
@role_required("manager", "admin", "livreur")
def export_clients_magasin_excel():
    """
    Exporter les clients du magasin avec leurs statistiques en Excel
    ---
    tags:
      - Export
      - Clients
    summary: Export Excel des clients du magasin avec filtres et stats
    description: Cette route permet d’exporter au format Excel la liste des clients d’un magasin, incluant leurs statistiques. Les managers, admins et livreurs peuvent utiliser cette fonctionnalité. Les filtres sont appliqués si spécifiés.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer
      - name: nom
        in: query
        type: string
        required: false
        description: Filtrer par nom du client (recherche partielle)
      - name: telephone
        in: query
        type: string
        required: false
        description: Filtrer par numéro de téléphone
      - name: quartier
        in: query
        type: string
        required: false
        description: Filtrer par quartier
      - name: ville
        in: query
        type: string
        required: false
        description: Filtrer par ville
      - name: created_by_name
        in: query
        type: string
        required: false
        description: Filtrer par nom de la personne ayant créé le client

    responses:
      200:
        description: Fichier Excel généré et téléchargé avec succès
        schema:
          type: file
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé
      500:
        description: Erreur serveur lors de l’exportation
    """
    filters = {
        "nom": request.args.get("nom"),
        "telephone": request.args.get("telephone"),
        "quartier": request.args.get("quartier"),
        "ville": request.args.get("ville"),
        "created_by_name": request.args.get("created_by_name"),
    }

    user_id = get_jwt_identity()
    user = UserModel.get_user_by_id(user_id)
        
    if user['role'] == 'livreur':
        clients = get_clients_livreur(user_id)
    else:
        clients = get_clients_magasins(filters)

    
    # Génération du fichier Excel dans un Buffer
    buffer = export_clients_to_excel(clients)
    # Sauvegarde locale dans un dossier temporaire
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"clients_magasin_{now}.xlsx"
    save_path = os.path.join(current_app.root_path, "exports")
    os.makedirs(save_path, exist_ok=True)
    full_path = os.path.join(save_path, filename)
    
    with open(full_path, "wb") as f:
        f.write(buffer.getvalue())
    excel_file = export_clients_to_excel(clients)

    return send_file(
        full_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )





# Récupérer tous les clients d'un livreur avec le nombre de livraisons et le montant total classé par ordre décroisssant
# Retourne les meilleur clients

@client_bp.route("best/livreur/", methods=["GET"])
@jwt_required()
@role_required("livreur")
def get_meilleurs_clients_livreurs():
    """
    Récupérer les meilleurs clients d’un livreur
    ---
    tags:
      - Clients
    summary: Liste des meilleurs clients d’un livreur
    description: Cette route retourne les clients d’un livreur avec leurs statistiques de nombre de livraisons et montant total, triés par performance.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT du livreur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Liste des meilleurs clients récupérée avec succès
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
                example: "64b8fae5e3b9ab9c8dbf8f67"
              nom:
                type: string
                example: "Sophie Nguimfack"
              telephone:
                type: string
                example: "+237690112233"
              nombre_livraisons:
                type: integer
                example: 25
              montant_total:
                type: number
                format: float
                example: 523500.0
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé
      500:
        description: Erreur serveur lors de la récupération des données
    """
    current_user_id = get_jwt_identity()
    clients = get_meilleurs_clients_livreur(current_user_id)
    return jsonify(clients), 200

  
@client_bp.route("/best/managers/", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def get_meilleurs_clients():
    """
    Récupérer les meilleurs clients avec statistiques globales
    ---
    tags:
      - Clients
    summary: Liste des meilleurs clients pour admin/manager
    description: Cette route retourne la liste des meilleurs clients selon le nombre de livraisons et le montant total, accessible aux admins et managers.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT de l'utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Liste des meilleurs clients récupérée avec succès
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
                example: "64b8fae5e3b9ab9c8dbf8f67"
              nom:
                type: string
                example: "Alice Tchoumi"
              telephone:
                type: string
                example: "+237699001122"
              nombre_livraisons:
                type: integer
                example: 40
              montant_total:
                type: number
                format: float
                example: 1023500.0
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé
      500:
        description: Erreur serveur lors de la récupération des données
    """
    current_user_id = get_jwt_identity()
    clients = get_meilleurs_clients_total()
    return jsonify(clients), 200

  
