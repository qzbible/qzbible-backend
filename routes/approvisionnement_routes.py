# routes/approvisionnement_routes.py

from flask import Blueprint, request, jsonify
from services.approvisionnement_service import (
  approvisionner_livreur,
  get_approvisionner_service,
  delete_approvisionnement_service,
  get_approvisionnement_details_service
  )
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.inject_magasin_id import inject_magasin_id
from utils.decorators import role_required



approvisionnement_bp = Blueprint("approvisionnement", __name__)

@approvisionnement_bp.route("/approvisionnements", methods=["POST"])
@jwt_required()
@role_required("admin", "manager")
def approvisionner():
    """
    Approvisionner un livreur
    ---
    tags:
      - Approvisionnement
    summary: Approvisionner un livreur en produits
    description: >
      Cette route permet à un administrateur ou un manager d’approvisionner un livreur avec une liste de produits
      (identifiés par leurs IDs et quantités). Le `admin_id` est automatiquement injecté depuis le token JWT.

    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: Jeton JWT au format **Bearer &lt;token&gt;**
        default: Bearer
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - livreur_id
            - produits
          properties:
            livreur_id:
              type: string
              description: ID du livreur à approvisionner (24 caractères)
              example: "662b9cf48f5b4a1e24688d20"
            produits:
              type: array
              description: Liste des produits à approvisionner avec leur quantité
              items:
                type: object
                required:
                  - produit_id
                  - quantite
                properties:
                  produit_id:
                    type: string
                    description: ID du produit à approvisionner (24 caractères)
                    example: "662b9da88f5b4a1e24688d21"
                  quantite:
                    type: integer
                    minimum: 1
                    description: Quantité à approvisionner
                    example: 10

    responses:
      201:
        description: Approvisionnement effectué avec succès
      400:
        description: Données invalides ou requête mal formulée
      401:
        description: Non autorisé – Token manquant ou invalide
      403:
        description: Accès interdit – Rôle insuffisant
      500:
        description: Erreur serveur lors du traitement
    """
    data = request.get_json()
    data["admin_id"] = get_jwt_identity()
    data = inject_magasin_id(data)
    response, status = approvisionner_livreur(data)
    return jsonify(response), status



@approvisionnement_bp.route("/approvisionnements", methods=["GET"])
@role_required("admin", "manager", "staff")
@jwt_required()
def get_approvisionner():
    """
    Récupérer la liste des approvisionnements
    ---
    tags:
      - Approvisionnement
    summary: Liste des approvisionnements
    description: >
      Cette route permet aux utilisateurs ayant le rôle **admin**, **manager** ou **staff** de récupérer
      l’historique des approvisionnements effectués. Le système filtre automatiquement les résultats
      selon l'identité de l'utilisateur connecté via le token JWT.

    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: Jeton JWT au format **Bearer &lt;token&gt;**
        default: Bearer

    responses:
      200:
        description: Liste des approvisionnements récupérée avec succès
        schema:
          type: object
          properties:
            approvisionnements:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "662c0d4f6b5a4a1f25facc2b"
                  livreur_id:
                    type: string
                    example: "662b9cf48f5b4a1e24688d20"
                  produits:
                    type: array
                    items:
                      type: object
                      properties:
                        produit_id:
                          type: string
                          example: "662b9da88f5b4a1e24688d21"
                        quantite:
                          type: integer
                          example: 10
                  date:
                    type: string
                    format: date-time
                    example: "2025-07-11T10:30:00Z"
      401:
        description: Non autorisé – Token manquant ou invalide
      403:
        description: Accès interdit – Rôle insuffisant
      500:
        description: Erreur serveur lors de la récupération des approvisionnements
    """
    admin_or_manager_id = get_jwt_identity()
    response, status = get_approvisionner_service(admin_or_manager_id)
    return jsonify(response), status


# Suppression d'un approvisionnement
@approvisionnement_bp.route("/approvisionnements/<string:approvisionnement_id>", methods=["DELETE"])
@role_required("admin", "manager", "staff")
@jwt_required()
def delete_approvisionnement(approvisionnement_id):
    """
    Supprimer un approvisionnement
    ---
    tags:
      - Approvisionnement
    description: "Permet à un admin, manager ou staff de supprimer un approvisionnement."
    parameters:
      - in: path
        name: approvisionnement_id
        required: true
        type: string
        description: "ID de l’approvisionnement à supprimer"
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Jeton JWT au format **Bearer &lt;token&gt;**"
        default: Bearer
    responses:
      200:
        description: "Approvisionnement supprimé avec succès"
      404:
        description: "Approvisionnement non trouvé"
    """
    response, status = delete_approvisionnement_service(approvisionnement_id)
    return jsonify(response), status
  
  

# détails d'un approvisionnement
@approvisionnement_bp.route("/approvisionnements/<string:approvisionnement_id>", methods=["GET"])
@role_required("admin", "manager", "staff", "livreur")
@jwt_required()
def get_approvisionnement_details(approvisionnement_id):
    """
    Détails d’un approvisionnement
    ---
    tags:
      - Approvisionnement
    summary: Détails d’un approvisionnement spécifique
    description: >
      Cette route permet de récupérer les détails complets d’un approvisionnement à partir de son identifiant.
      Accessible aux rôles : **admin**, **manager**, **staff**, **livreur**.

    parameters:
      - name: approvisionnement_id
        in: path
        required: true
        type: string
        description: ID de l’approvisionnement à consulter (24 caractères)
        example: "662b9c2c8f5b4a1e24688d1c"
      - in: header
        name: Authorization
        required: true
        type: string
        description: Jeton JWT au format **Bearer &lt;token&gt;**
        default: Bearer

    responses:
      200:
        description: Approvisionnement trouvé avec succès
        schema:
          type: object
          properties:
            _id:
              type: string
              example: "662b9c2c8f5b4a1e24688d1c"
            livreur_id:
              type: string
              example: "662b9cf48f5b4a1e24688d20"
            produits:
              type: array
              items:
                type: object
                properties:
                  produit_id:
                    type: string
                    example: "662b9da88f5b4a1e24688d21"
                  quantite:
                    type: integer
                    example: 10
            date:
              type: string
              format: date-time
              example: "2025-07-11T10:30:00Z"
      404:
        description: Approvisionnement non trouvé
      401:
        description: Non autorisé – Token manquant ou invalide
      403:
        description: Accès interdit – Rôle insuffisant
      500:
        description: Erreur serveur lors de la récupération des détails
    """
    result = get_approvisionnement_details_service(approvisionnement_id)
    if result:
        return jsonify(result), 200
    else:
        return jsonify({"message": "Approvisionnement non trouvé"}), 404
