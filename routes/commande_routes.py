from flask import Blueprint, request, jsonify
from schemas.commande_schema import CreateCommandeSchema, UpdateCommandeSchema
from services.commande_service import (
    create_commande_service,
    get_all_commandes_service,
    get_commande_by_id_service,
    get_commandes_by_client_service,
    get_commandes_by_magasin_service,
    update_commande_service,
    delete_commande_service
)

commande_bp = Blueprint("commande", __name__, url_prefix="/commandes")


@commande_bp.route("/create", methods=["POST"])
def create_commande():
    """
    Créer une nouvelle commande.
    ---
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          id: CreateCommande
          required:
            - client_id
            - magasin_id
            - produits
            - montant_total
            - statut
            - adresse_livraison
          properties:
            client_id:
              type: string
            magasin_id:
              type: string
            produits:
              type: array
              items:
                type: object
                properties:
                  produit_id:
                    type: string
                  nom:
                    type: string
                  quantite:
                    type: integer
                  prix:
                    type: number
            montant_total:
              type: number
            statut:
              type: string
            adresse_livraison:
              type: string
    responses:
      201:
        description: Commande créée avec succès
      400:
        description: Données invalides
    """
    data = request.get_json()
    errors = CreateCommandeSchema().validate(data)
    if errors:
        return jsonify({"errors": errors}), 400
    return create_commande_service(data)


@commande_bp.route("/", methods=["GET"])
def get_commandes():
    """
    Récupérer la liste de toutes les commandes.
    ---
    responses:
      200:
        description: Liste des commandes
    """
    return jsonify(get_all_commandes_service()), 200


@commande_bp.route("/<commande_id>", methods=["GET"])
def get_commande(commande_id):
    """
    Récupérer une commande par ID.
    ---
    parameters:
      - in: path
        name: commande_id
        type: string
        required: true
    responses:
      200:
        description: Détails de la commande
      404:
        description: Commande non trouvée
    """
    commande = get_commande_by_id_service(commande_id)
    if not commande:
        return jsonify({"error": "Commande non trouvée"}), 404
    return jsonify(commande), 200


@commande_bp.route("/client/<client_id>", methods=["GET"])
def get_commandes_client(client_id):
    """
    Récupérer les commandes d’un client.
    ---
    parameters:
      - in: path
        name: client_id
        type: string
        required: true
    responses:
      200:
        description: Liste des commandes du client
    """
    return jsonify(get_commandes_by_client_service(client_id)), 200


@commande_bp.route("/magasin/<magasin_id>", methods=["GET"])
def get_commandes_magasin(magasin_id):
    """
    Récupérer les commandes d’un magasin.
    ---
    parameters:
      - in: path
        name: magasin_id
        type: string
        required: true
    responses:
      200:
        description: Liste des commandes du magasin
    """
    return jsonify(get_commandes_by_magasin_service(magasin_id)), 200


@commande_bp.route("/<commande_id>", methods=["PUT"])
def update_commande(commande_id):
    """
    Mettre à jour une commande.
    ---
    parameters:
      - in: path
        name: commande_id
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          id: UpdateCommande
          properties:
            produits:
              type: array
              items:
                type: object
                properties:
                  produit_id:
                    type: string
                  nom:
                    type: string
                  quantite:
                    type: integer
                  prix:
                    type: number
            montant_total:
              type: number
            statut:
              type: string
            adresse_livraison:
              type: string
    responses:
      200:
        description: Commande mise à jour
      400:
        description: Données invalides
    """
    data = request.get_json()
    errors = UpdateCommandeSchema().validate(data)
    if errors:
        return jsonify({"errors": errors}), 400
    update_commande_service(commande_id, data)
    return jsonify({"message": "Commande mise à jour"}), 200


@commande_bp.route("/<commande_id>", methods=["DELETE"])
def delete_commande(commande_id):
    """
    Supprimer une commande par ID.
    ---
    parameters:
      - in: path
        name: commande_id
        type: string
        required: true
    responses:
      200:
        description: Commande supprimée avec succès
    """
    delete_commande_service(commande_id)
    return jsonify({"message": "Commande supprimée"}), 200
