# routes/produit_routes.py
from datetime import datetime
import json
import os
from werkzeug.exceptions import BadRequest
from utils.decorators import admin_required, manager_required
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from utils.decorators import role_required
from utils.inject_magasin_id import inject_magasin_id
from schemas.produit_schema import CreateProduitSchema, UpdateProduitSchema
from models.user_model import UserModel
from services.produit_service import (
    create_produit_service,
    get_produits_by_magasin_service,
    update_produit_service,
    delete_produit_service,
    get_produit_by_id_service,
    get_mouvements_stock_service,
    get_meilleurs_produits_livreur,
    get_meilleurs_produits_total,
    approvisionner_produit_service
)
from services.import_files_services import import_produits_from_excel
from services.export_files_services import export_produits_to_excel
from services.stats_staff_service import get_suggestions_service
from services.stock_livreur_service import get_stock_livreur_avec_details

produit_bp = Blueprint("produit", __name__)





# Route pour créer un produit

@produit_bp.route("/produits", methods=["POST"])
@role_required("admin", "manager")
@jwt_required()
def create_produit():
    """
    Création d'un produit
    ---
    tags:
      - Produits
    consumes:
      - multipart/form-data
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        example: "Bearer votre.jwt.token"
        description: JWT token nécessaire pour l'autorisation
        default: Bearer
      - in: formData
        name: nom
        required: true
        type: string
        example: "Chocolat Noir 70%"
        description: Nom du produit
      - in: formData
        name: description
        required: false
        type: string
        example: "Tablette de chocolat noir bio 100g"
        description: Description détaillée du produit
      - in: formData
        name: prix
        required: true
        type: number
        format: float
        example: 2.99
        description: Prix unitaire du produit
      - in: formData
        name: quantite
        required: true
        type: integer
        example: 50
        description: Quantité initiale en stock
      - in: formData
        name: unite
        required: true
        type: string
        example: "unité"
        description: Unité de mesure (kg, litre, unité, etc.)
      - in: formData
        name: image
        required: false
        type: file
        description: Image du produit (format JPG/PNG)
      - in: formData
        name: categorie_id
        required: true
        type: string
        example: "605c72ef1532072e7c32ed47"
        description: ID de la catégorie associée
      - in: formData
        name: conditionnements
        required: false
        type: string
        example: '[{"nom": "Lot de 5", "facteur": 5, "prix_conditionnement": 12.99}]'
        description: JSON string des conditionnements disponibles
    responses:
      201:
        description: Produit créé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Produit créé"
            produit_id:
              type: string
              example: "607f1f77bcf86cd799439011"
      400:
        description: Erreur de validation des données
        schema:
          type: object
          properties:
            errors:
              type: object
              example: {"nom": ["Ce champ est obligatoire"]}
      409:
        description: Un produit avec ce nom existe déjà dans ce magasin
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Ce produit existe déjà dans ce magasin"
      401:
        description: Non autorisé (token invalide ou manquant)
      403:
        description: Accès refusé (rôle insuffisant)
    security:
      - JWT: []
    """
    try:
        data = request.form.to_dict()
        data = inject_magasin_id(data)
        image_file = request.files.get("image")
        
        # Nettoyer conditionnements si présent sous forme de string JSON
        if "conditionnements" in data and isinstance(data["conditionnements"], str):
            try:
                data["conditionnements"] = json.loads(data["conditionnements"])
            except json.JSONDecodeError:
                data["conditionnements"] = []
        
        errors = CreateProduitSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        return create_produit_service(data, image_file)
    except BadRequest as e:
        return jsonify({"message": str(e)}), 400



# récupérer tous les produits d'un magasin
@produit_bp.route("/produits", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def get_produits_by_magasin():
    """
    Récupérer les produits du magasin connecté
    ---
    tags:
      - Produits
    summary: Obtenir la liste des produits avec filtres avancés
    description: >
      Récupère les produits du **magasin associé** à l'utilisateur authentifié.
      <br><br>
      **Fonctionnalités :**
      - Filtrage par nom (recherche partielle)
      - Filtrage par état de stock
      - Filtrage par catégorie
      - Filtrage par plage de prix
      - Filtrage par quantité disponible
      - Tri implicite par date de création (du plus récent au plus ancien)

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Token JWT (format `Bearer <votre_token>`)
        example: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
      - name: nom
        in: query
        type: string
        required: false
        description: Filtre par nom (insensible à la casse, recherche partielle)
        example: Chocolat
      - name: etat
        in: query
        type: string
        enum: [en stock, en rupture, en commande]
        required: false
        description: Filtre par état du stock
        example: en stock
      - name: categorie_nom
        in: query
        type: string
        required: false
        description: Filtre par nom exact de catégorie
        example: Epicerie
      - name: prix_min
        in: query
        type: number
        format: float
        required: false
        description: Prix unitaire minimum (inclus)
        example: 5.0
      - name: prix_max
        in: query
        type: number
        format: float
        required: false
        description: Prix unitaire maximum (inclus)
        example: 50.0
      - name: quantite_min
        in: query
        type: integer
        required: false
        description: Quantité minimum en stock (inclus)
        example: 10
      - name: quantite_max
        in: query
        type: integer
        required: false
        description: Quantité maximum en stock (inclus)
        example: 100
      - name: page
        in: query
        type: integer
        required: false
        description: Numéro de page (pour pagination, 1 par défaut)
        example: 1
      - name: limit
        in: query
        type: integer
        required: false
        description: Nombre d'éléments par page (10 par défaut, max 100)
        example: 20

    responses:
      200:
        description: Liste paginée des produits correspondants aux filtres
        schema:
          type: object
          properties:
            produits:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "605c72ef1532072e7c32ed49"
                  nom:
                    type: string
                    example: "Chocolat Noir 70%"
                  description:
                    type: string
                    example: "Tablette 100g de chocolat bio"
                  prix:
                    type: number
                    format: float
                    example: 3.99
                  quantite:
                    type: integer
                    example: 45
                  etat:
                    type: string
                    example: "en stock"
                  image:
                    type: string
                    example: "chocolat_noir.jpg"
                  categorie:
                    type: object
                    properties:
                      _id:
                        type: string
                        example: "605c72ef1532072e7c32ed47"
                      nom:
                        type: string
                        example: "Epicerie sucrée"
                  conditionnements:
                    type: array
                    items:
                      type: object
                      properties:
                        nom:
                          type: string
                          example: "Lot de 5"
                        prix_conditionnement:
                          type: number
                          example: 18.0
                        economie:
                          type: number
                          example: -2.0
            pagination:
              type: object
              properties:
                page:
                  type: integer
                  example: 1
                total_pages:
                  type: integer
                  example: 3
                total_produits:
                  type: integer
                  example: 27
      400:
        description: Paramètres de filtre invalides
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Le paramètre 'prix_max' doit être un nombre"
      401:
        description: |
          Non autorisé :
          - Token manquant/invalide
          - Rôle insuffisant
      404:
        description: Magasin non trouvé
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Erreur lors de la récupération des produits"

    security:
      - JWT: []
    """
    data = {}
    data = inject_magasin_id(data)

    magasin_id = data.get("magasin_id")
    filters = {
        "nom": request.args.get("nom"),
        "etat": request.args.get("etat"),
        "categorie_nom": request.args.get("categorie_nom"),
        "prix_min": request.args.get("prix_min", type=float),
        "prix_max": request.args.get("prix_max", type=float),
        "quantite_min": request.args.get("quantite_min", type=int),
        "quantite_max": request.args.get("quantite_max", type=int),
    }

    produits = get_produits_by_magasin_service(magasin_id, filters)

    for p in produits:
        p["_id"] = str(p["_id"])
        p["magasin_id"] = str(p["magasin_id"])
        p["categorie_id"] = str(p["categorie_id"])
    return jsonify(produits), 200



# export des produits du manager sous formats excel
@produit_bp.route("/produits/export", methods=["GET"])
@jwt_required()
@role_required("admin", "manager", "livreur", "staff")
def export_produits_excel():
    """
    Exporter les produits au format Excel
    ---
    tags:
      - Export
    summary: Export Excel des produits disponibles
    description: >
      Cette route permet d’exporter la liste des produits d’un magasin ou du stock d’un livreur (avec détails)
      en fonction de plusieurs filtres (nom, état, prix, quantité, etc.).
      Le fichier généré est retourné au format Excel (.xlsx).
    
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT (format **Bearer &lt;token&gt;**)
        default: Bearer
      - in: query
        name: nom
        type: string
        required: false
        description: Nom du produit à filtrer
      - in: query
        name: etat
        type: string
        required: false
        description: État du produit (actif/inactif)
      - in: query
        name: categorie_nom
        type: string
        required: false
        description: Nom de la catégorie
      - in: query
        name: prix_min
        type: number
        required: false
        description: Prix minimum du produit
      - in: query
        name: prix_max
        type: number
        required: false
        description: Prix maximum du produit
      - in: query
        name: quantite_min
        type: integer
        required: false
        description: Quantité minimale en stock
      - in: query
        name: quantite_max
        type: integer
        required: false
        description: Quantité maximale en stock

    responses:
      200:
        description: Fichier Excel généré avec succès
        content:
          application/vnd.openxmlformats-officedocument.spreadsheetml.sheet:
            schema:
              type: string
              format: binary
      401:
        description: Non autorisé – Token manquant ou invalide
      403:
        description: Accès interdit – Rôle insuffisant
      500:
        description: Erreur lors de la génération ou de l’export du fichier
    """
    data = inject_magasin_id({})
    magasin_id = data.get("magasin_id")

    # Filtres
    filters = {
        "nom": request.args.get("nom"),
        "etat": request.args.get("etat"),
        "categorie_nom": request.args.get("categorie_nom"),
        "prix_min": request.args.get("prix_min", type=float),
        "prix_max": request.args.get("prix_max", type=float),
        "quantite_min": request.args.get("quantite_min", type=int),
        "quantite_max": request.args.get("quantite_max", type=int),
    }

    # vérifier le role de l'utilisateurs qui appelle cette route
    user_id = get_jwt_identity()
    user = UserModel.find_by_id(user_id)
    if user['role'] == 'livreur':
        produits = get_stock_livreur_avec_details(user_id)
    else:
        produits = get_produits_by_magasin_service(magasin_id, filters)

    # Génération du fichier Excel dans un buffer
    buffer = export_produits_to_excel(produits)

    #  Sauvegarde locale dans un dossier temporaire
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"produits_{now}.xlsx"
    save_path = os.path.join(current_app.root_path, "exports")
    os.makedirs(save_path, exist_ok=True)
    full_path = os.path.join(save_path, filename)

    with open(full_path, "wb") as f:
        f.write(buffer.getvalue())

    # Retourne le fichier à l'utilisateur
    return send_file(
        full_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )



@produit_bp.route("/produits/magasin/", methods=["GET"])
@jwt_required()
@role_required("livreur")
def get_product_stock_livreur():
    """
    Récupérer le stock disponible pour un livreur
    ---
    tags:
      - Produits
    summary: Obtenir les produits disponibles pour livraison
    description: >
      Cette endpoint permet aux **livreurs** de récupérer la liste des produits disponibles
      dans leur magasin attitré, avec des informations spécifiques utiles pour la livraison.
      <br><br>
      **Inclus :**
      - Détails complets des produits
      - Localisation du stock
      - Quantités immédiatement disponibles
      - Informations sur les conditionnements

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Token JWT (format `Bearer <token>`)
        example: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
      - name: en_stock
        in: query
        type: boolean
        required: false
        description: Filtrer uniquement les produits disponibles (quantité > 0)
        default: true
      - name: tri
        in: query
        type: string
        enum: [nom, prix_croissant, prix_decroissant]
        required: false
        description: Critère de tri des résultats
        example: prix_croissant

    responses:
      200:
        description: Liste des produits disponibles pour livraison
        schema:
          type: object
          properties:
            magasin:
              type: object
              properties:
                nom:
                  type: string
                  example: "Supermarché Central"
                adresse:
                  type: string
                  example: "123 Rue Principale, Ville"
            produits:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    example: "507f1f77bcf86cd799439011"
                  nom:
                    type: string
                    example: "Eau Minérale 1L"
                  description:
                    type: string
                    example: "Pack de 6 bouteilles"
                  image_url:
                    type: string
                    example: "/uploads/images/eau_minerale.jpg"
                  prix_unitaire:
                    type: number
                    format: float
                    example: 1.20
                  quantite_disponible:
                    type: integer
                    example: 42
                  emplacement:
                    type: string
                    example: "Rayon 3, Étagère B"
                  conditionnements:
                    type: array
                    items:
                      type: object
                      properties:
                        nom:
                          type: string
                          example: "Pack 6"
                        prix:
                          type: number
                          example: 6.0
                        economie:
                          type: number
                          example: 1.2
      401:
        description: |
          Non autorisé :
          - Token invalide/expiré
          - Rôle incorrect (non livreur)
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Authentification requise"
      404:
        description: |
          Ressource non trouvée :
          - Livreur non associé à un magasin
          - Aucun produit disponible
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Erreur lors de la récupération du stock"

    security:
      - JWT: []
    """
    livreur_id = get_jwt_identity()
    produits = get_stock_livreur_avec_details(livreur_id)
    return jsonify(produits), 200




#Mettre à jour les données d'un produit

@produit_bp.route("/produits/<produit_id>", methods=["PUT"])
@jwt_required()
@role_required("admin", "livreur", "manager")
def update_produit(produit_id):
  
    """
    Mettre à jour un produit existant
    ---
    tags:
      - Produits
    summary: Mise à jour partielle ou complète d'un produit
    description: |
      Permet de modifier les informations d'un produit existant.
      <br><br>
      **Fonctionnalités :**
      - Mise à jour partielle (seuls les champs fournis sont modifiés)
      - Modification de l'image du produit
      - Gestion des conditionnements
      - Historique des modifications (via admin_id)
      <br><br>
      **Rôles autorisés :** Admin, Manager, Livreur (avec restrictions)

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Token JWT (format `Bearer <token>`)
        example: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
      - name: produit_id
        in: path
        type: string
        required: true
        description: ID du produit à modifier
        example: "507f1f77bcf86cd799439011"
      - name: nom
        in: formData
        type: string
        required: false
        description: Nouveau nom du produit
        example: "Nouveau nom du produit"
      - name: description
        in: formData
        type: string
        required: false
        description: Nouvelle description
        example: "Nouvelle description plus détaillée"
      - name: prix
        in: formData
        type: number
        format: float
        required: false
        description: Nouveau prix unitaire
        example: 15.99
      - name: quantite
        in: formData
        type: integer
        required: false
        description: Nouvelle quantité en stock
        example: 150
      - name: image
        in: formData
        type: file
        required: false
        description: Nouvelle image du produit (laisser vide pour conserver l'actuelle)
      - name: conditionnements
        in: formData
        type: string
        required: false
        description: |
          JSON string des conditionnements mis à jour.
          Format: `[{"nom": "Lot", "facteur": 5, "prix_conditionnement": 45.0}]`
        example: '[{"nom": "Pack familial", "facteur": 3, "prix_conditionnement": 40.0}]'
      - name: categorie_id
        in: formData
        type: string
        required: false
        description: Nouvelle catégorie ID
        example: "605c72ef1532072e7c32ed47"

    responses:
      200:
        description: Produit mis à jour avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Produit mis à jour avec succès"
            produit_id:
              type: string
              example: "507f1f77bcf86cd799439011"
            modifications:
              type: array
              items:
                type: string
              example: ["nom", "prix"]
      400:
        description: |
          Erreurs de validation :
          - Données invalides
          - JSON des conditionnements mal formatté
        schema:
          type: object
          properties:
            errors:
              type: object
              example: {"prix": ["Doit être un nombre positif"]}
      401:
        description: Non autorisé (token invalide ou manquant)
      403:
        description: |
          Accès refusé :
          - Rôle insuffisant
          - Tentative de modification hors de son magasin (pour livreurs/managers)
      404:
        description: Produit non trouvé
      500:
        description: Erreur serveur lors de la mise à jour

    security:
      - JWT: []
    """
    try:
        data = request.form.to_dict()
        image_file = request.files.get("image")
        #data = inject_magasin_id(data)
        data['admin_id'] = get_jwt_identity()  # Ajout de l'ID de l'utilisateur qui met à jour le produit
        
        # Convertir conditionnements s’ils sont passés en JSON string
        if "conditionnements" in data and isinstance(data["conditionnements"], str):
            import json
            try:
                data["conditionnements"] = json.loads(data["conditionnements"])
            except json.JSONDecodeError:
                data["conditionnements"] = []
 
        errors = UpdateProduitSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400

        return  update_produit_service(produit_id, data, image_file)
        
        
      
    except BadRequest as e:
        return jsonify({"message": str(e)}), 400



# Supprimer un produit de la base de données
@produit_bp.route("/produits/<produit_id>", methods=["DELETE"])
@jwt_required()
@role_required("admin", "manager")
def delete_produit(produit_id):
    """
    Supprimer un produit par son ID
    ---
    tags:
      - Produits
    summary: Suppression d’un produit existant
    description: >
      Cette route permet aux **admins** ou **managers** de supprimer un produit
      à partir de son identifiant (`produit_id`).

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton d'authentification JWT (format Bearer <token>)
        default: Bearer
      - name: produit_id
        in: path
        type: string
        required: true
        description: Identifiant unique du produit à supprimer
        example: 605c72ef1532072e7c32ed49

    responses:
      200:
        description: Produit supprimé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: Produit supprimé
      404:
        description: Produit non trouvé
      401:
        description: Jeton d'authentification manquant ou invalide
      403:
        description: Rôle non autorisé
      500:
        description: Erreur serveur lors de la suppression
    """
    delete_produit_service(produit_id)
    return jsonify({"message": "Produit supprimé"}), 200

 
 
  
# Avoir les détails d'un prodtuit

@produit_bp.route("/produits/<produit_id>", methods=["GET"])
@jwt_required()
@role_required("admin", "livreur", "manager")
def get_produit_by_id(produit_id):
    """
    Récupérer un produit par son ID
    ---
    tags:
      - Produits
    summary: Détails d’un produit
    description: >
      Cette route permet de récupérer les détails complets d’un produit à partir
      de son identifiant. Accessible uniquement aux utilisateurs ayant un rôle
      **admin**, **manager**, ou **livreur**.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT au format Bearer <token>
        default: Bearer
      - name: produit_id
        in: path
        type: string
        required: true
        description: ID du produit à consulter
        example: 605c72ef1532072e7c32ed49

    responses:
      200:
        description: Produit récupéré avec succès
        schema:
          type: object
          properties:
            _id:
              type: string
              example: "605c72ef1532072e7c32ed49"
            nom:
              type: string
              example: "Produit Exemple"
            description:
              type: string
              example: "Description du produit"
            prix:
              type: number  
              format: float
              example: 19.99
            quantite:
              type: integer
              example: 100
            etat:
              type: string
              example: en stock
            categorie_id:
              type: string
              example: "605c72ef1532072e7c32ed47"
            magasin_id:
              type: string
              example: "605c72ef1532072e7c32ed48"
      401:
        description: Jeton manquant ou invalide
      403:
        description: Accès interdit pour ce rôle
      404:
        description: Produit non trouvé
      500:
        description: Erreur serveur inattendue
    """
    produit = get_produit_by_id_service(produit_id)
    if not produit:
        return jsonify({"message": "Produit non trouvé"}), 404
    produit["_id"] = str(produit["_id"])
    produit["magasin_id"] = str(produit["magasin_id"])
    produit["categorie_id"] = str(produit["categorie_id"])
    return jsonify(produit), 200


# Récupérer tous les mouvements de stock d'un produit
@produit_bp.route("/<produit_id>/mouvements", methods=["GET"])
@role_required("admin", "manager")
def get_mouvements_stock(produit_id):
    """
    Récupérer les mouvements de stock d'un produit.
    ---
    tags:
      - Produits
    parameters:
      - in: path
        name: produit_id
        required: true
        type: string
        description: ID du produit
      - in: query
        name: type
        required: false
        type: string
        description: Filtrer par type de mouvement
    responses:
      200:
        description: Liste des mouvements de stock
      404:
        description: Produit non trouvé ou aucun mouvement
    """
    type_mouvement = request.args.get("type")  # Filtre optionnel
    result, status = get_mouvements_stock_service(produit_id, type_mouvement)
    return jsonify(result), status




# Fonctions statistiques
"""
Retourne les produits les plus vendus par un livreur, classés par quantité totale 
livrée (du plus vendu au moins vendu) 
"""
@produit_bp.route("/produits/best/livreur/", methods=["GET"])
@jwt_required()
@role_required("admin", "manager", "livreur")
def get_best_product_per_livreur():
    """
    Produits les plus livrés par le livreur
    ---
    tags:
      - Produits
    summary: Produits les plus livrés
    description: >
      Retourne les produits les plus livrés par le livreur connecté, classés par
      **quantité totale livrée** (du plus vendu au moins vendu).<br>
      Accessible aux rôles : **admin**, **manager**, **livreur**.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT d’authentification (format **Bearer &lt;token&gt;**)
        default: Bearer 

    responses:
      200:
        description: Liste des produits les plus livrés
        schema:
          type: array
          items:
            type: object
            properties:
              produit_id:
                type: string
                example: "60df5bf8f0b2f81d1c4c9b4a"
              nom:
                type: string
                example: "Savon antiseptique"
              quantite_totale:
                type: integer
                example: 125
      401:
        description: Accès non autorisé ou token manquant
      403:
        description: Rôle non autorisé
      500:
        description: Erreur interne
    """
    current_user_id = get_jwt_identity()
    best_products = get_meilleurs_produits_livreur(current_user_id)
    return jsonify(best_products), 200

    

@produit_bp.route("/produits/best/managers", methods=["GET"])
@role_required("admin", "manager", "livreur")
def get_best_product_total():
    """
    Obtenir les produits les plus vendus
    ---
    tags:
      - Produits
    summary: Statistiques des produits les plus vendus
    description: |
      Retourne les produits les plus vendus classés par quantité totale livrée.
      <br><br>
      **Fonctionnalités :**
      - Vue globale pour les administrateurs/managers
      - Filtrage par livreur spécifique
      - Liste des livreurs disponibles incluse dans la réponse
      <br><br>
      **Permissions :**
      - Admin/Manager : accès complet
      - Livreur : seulement ses propres statistiques

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Token JWT (format `Bearer <token>`)
        example: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
      - name: livreur_id
        in: query
        type: string
        required: false
        description: |
          Filtre par livreur spécifique (obligatoire pour les livreurs).
          Les managers/admins peuvent omettre ce paramètre pour une vue globale.
        example: "507f1f77bcf86cd799439011"
      - name: limit
        in: query
        type: integer
        required: false
        default: 10
        description: Nombre maximum de produits à retourner (max 50)
        example: 5
      - name: periode
        in: query
        type: string
        enum: [semaine, mois, trimestre, annee, tout]
        required: false
        default: mois
        description: Période d'analyse des ventes
        example: mois

    responses:
      200:
        description: Statistiques des meilleurs produits
        schema:
          type: object
          properties:
            best_products:
              type: array
              items:
                type: object
                properties:
                  produit_id:
                    type: string
                    example: "507f1f77bcf86cd799439012"
                  nom:
                    type: string
                    example: "Eau Minérale 1L"
                  image_url:
                    type: string
                    example: "/uploads/images/eau_minerale.jpg"
                  quantite_vendue:
                    type: integer
                    example: 150
                  pourcentage:
                    type: number
                    format: float
                    example: 25.5
                  chiffre_affaires:
                    type: number
                    format: float
                    example: 450.0
            livreurs:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "507f1f77bcf86cd799439011"
                  nom_complet:
                    type: string
                    example: "Jean Dupont"
                  email:
                    type: string
                    example: "jean.dupont@example.com"
      400:
        description: |
          Requête invalide :
          - Livreur non spécifié (pour les livreurs)
          - Paramètres de filtre invalides
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Un livreur_id doit être spécifié"
      401:
        description: Non autorisé (token invalide ou manquant)
      403:
        description: Accès refusé (rôle insuffisant)
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Erreur lors de la récupération des statistiques"

    security:
      - JWT: []
    """
  
    from services.user_service import get_livreur_service
    livreur_id = request.args.get("livreur_id", None)
    try:
        best_products = get_meilleurs_produits_total(livreur_id)
        # Appel au service de récuparation des livreurs
        livreur_result = get_livreur_service()
        if livreur_result["status"] != 200:
            raise Exception("Impossible de récupérer les livreurs")
        return jsonify({
            "best_products": best_products,
            "livreurs": livreur_result["livreurs"]
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erreur interne : {str(e)}"}), 500

    
  
# Importer des produits depuis un fichier Excel
@produit_bp.route("/produits/import", methods=["POST"])
@jwt_required()
@role_required("admin", "manager")
def import_produits():
    """
    Importer des produits depuis un fichier Excel
    ---
    tags:
      - Produits
    summary: Importation de produits par fichier Excel
    description: >
      Permet d'importer en masse des produits depuis un fichier Excel (`.xlsx`) 
      pour un magasin donné. Seuls les rôles **admin** et **manager** peuvent exécuter cette action.

    consumes:
      - multipart/form-data

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT d’authentification (format **Bearer &lt;token&gt;**)
        default: Bearer 
      - name: fichier
        in: formData
        type: file
        required: true
        description: Fichier Excel à importer (`.xlsx`)

    responses:
      200:
        description: Produits importés avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Importation réussie"
      400:
        description: Fichier ou données invalides
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Aucun fichier fourni"
      500:
        description: Erreur interne lors de l'importation
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Erreur lors de l'importation : Nom de la feuille introuvable"
    """
    fichier = request.files.get("fichier")
    if not fichier:
        return jsonify({"error": "Aucun fichier fourni"}), 400
    try:
        data = request.form.to_dict()
        data = inject_magasin_id(data)
        magasin_id = data.get("magasin_id")
        if not magasin_id:
            return jsonify({"error": "Magasin ID manquant"}), 400

        result = import_produits_from_excel(fichier, magasin_id)
        return jsonify(result), result[1]
    except Exception as e:
        return jsonify({"error": f"Erreur lors de l'importation : {str(e)}"}), 500

  

@produit_bp.route("/produits/suggestions", methods=["GET"])
@role_required("admin", "manager", "livreur", "staff")
def suggere_images():
    """
    Suggérer des images pour un produit en fonction des mots-clés
    ---
    tags:
      - Produits
    summary: Suggestions d’images produit via IA ou recherche contextuelle
    description: >
      Retourne des images suggérées à partir du nom, de la description, de la catégorie ou des tags d’un produit.

    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT d’authentification (format **Bearer &lt;token&gt;**)
        default: Bearer 
      - name: nom
        in: query
        type: string
        required: false
        description: Nom du produit
        example: Banane Bio
      - name: description
        in: query
        type: string
        required: false
        description: Description courte du produit
        example: "Fruits tropicaux riches en potassium"
      - name: categorie
        in: query
        type: string
        required: false
        description: Nom de la categorie du produit
        example: Fruits
      - name: tags
        in: query
        type: array
        items:
          type: string
        collectionFormat: multi
        required: false
        description: Liste de mots-cles lies au produit 

    responses:
      200:
        description: Images suggerees avec succes
        schema:
          type: object
          properties:
            images:
              type: array
              items:
                type: string
                example: "https://example.com/images/banane_bio.png"
      400:
        description: Paramètres insuffisants ou invalides
      500:
        description: Erreur serveur lors de la suggestion
    """
    nom = request.args.get("nom")
    description = request.args.get("description")
    categorie = request.args.get("categorie")
    tags = request.args.getlist("tags")  # /suggestions?tags=fruit&tags=bio

    images = get_suggestions_service(nom, categorie,description, tags)
    return {"images": images}, 200  
  

@produit_bp.route("/produits/<produit_id>/approvisionner", methods=["POST"])
@jwt_required()
@role_required("admin", "manager")
def approvisionner_produit(produit_id):
    """
    Approvisionner un produit
    ---
    tags:
      - Produits
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Jeton JWT d’authentification (format **Bearer &lt;token&gt;**)
        default: Bearer
      - in: path
        name: produit_id
        required: true
        type: string
        description: ID du produit à approvisionner
        example: "605c72ef1532072e7c32ed49"
        
      - in: formData
        name: quantite
        required: true
        type: integer
        description: Quantité à ajouter au stock
        example: 50
    responses:
      200:
        description: Produit approvisionné avec succès
      404:
        description: Produit non trouvé
    """
    data = request.get_json()
    data['admin_id'] = get_jwt_identity()
    try:
        quantite = int(data.get("quantite", 0))
        if quantite <= 0:
            return jsonify({"error": "La quantité doit être supérieure à 0"}), 400
        
        result = approvisionner_produit_service(produit_id, data)
        return jsonify(result), 200
    except ValueError:
        return jsonify({"error": "Quantité invalide"}), 400