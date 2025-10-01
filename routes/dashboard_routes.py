from flask import Blueprint, jsonify, request
from services.stock_livreur_service import get_stock_par_categorie_pour_livreur
from services.produit_service import get_stock_par_categorie_total
from utils.decorators import role_required
from services.stats_livreur_service import (
get_villes_livraison_livreur,
get_revenus_par_periode_par_livreur,
get_statistiques_paiement_par_livreur,
get_chiffre_affaires_total_par_livreur,
get_nombre_livraisons_total_par_livreur,
get_nombre_produits_uniques_par_livreur,
get_nombre_clients_uniques_par_livreur,
)
from utils.inject_magasin_id import inject_magasin_id
from services.stats_manager_service import (
    get_chiffre_affaires_total,
    get_nombre_livraisons_total,
    get_nombre_clients_total_livre,
    get_nombre_produits_livres,
    get_statistiques_paiement_total,
    get_revenus_par_periode_total,
    get_villes_livraison_total
)

from flask_jwt_extended import jwt_required, get_jwt_identity  
from utils.decorators import livreur_required

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/livreurs/stock_par_categorie", methods=["GET"])
@jwt_required()
@livreur_required
def get_stock_livreur_par_categorie():
    """
    Obtenir le stock du livreur réparti par catégorie
    ---
    tags:
      - Statistiques
      - Livreurs
    summary: Stock du livreur par catégorie
    description: Cette route retourne la liste des produits en stock pour le livreur connecté, regroupés par catégorie.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT du livreur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Stock par catégorie récupéré avec succès
        schema:
          type: object
          properties:
            categories:
              type: array
              items:
                type: object
                properties:
                  categorie:
                    type: string
                    example: "Boissons"
                  quantite:
                    type: integer
                    example: 150
                  produits:
                    type: array
                    items:
                      type: object
                      properties:
                        produit_id:
                          type: string
                          example: "64b8fae5e3b9ab9c8dbf8f67"
                        nom:
                          type: string
                          example: "Coca-Cola 33cl"
                        quantite_stock:
                          type: integer
                          example: 50
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (non livreur)
      500:
        description: Erreur serveur lors de la récupération du stock
    """
    livreur_id = get_jwt_identity()
    #print("Livreur ID depuis le token :", livreur_id)
    try:
        result = get_stock_par_categorie_pour_livreur(livreur_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": "Erreur lors de la récupération du stock", "error": str(e)}), 500




@dashboard_bp.route("/livreurs/villes_livraison", methods=["GET"])
@jwt_required()
@livreur_required
def get_villes_livraison():
    """
    Récupérer les zones de livraison maximales d’un livreur
    ---
    tags:
      - Statistiques
      - Livreurs
    summary: Zones de livraison d’un livreur
    description: Cette route retourne la liste des villes dans lesquelles le livreur connecté est autorisé à effectuer des livraisons.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT du livreur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Liste des villes de livraison récupérée avec succès
        schema:
          type: object
          properties:
            villes:
              type: array
              items:
                type: string
              example: ["Yaoundé", "Douala", "Bafoussam"]
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (non livreur)
      500:
        description: Erreur serveur lors de la récupération des villes de livraison
    """
    livreur_id = get_jwt_identity()
    print("Livreur ID depuis le token :", livreur_id)
    try:
        result = get_villes_livraison_livreur(livreur_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": "Erreur lors de la récupération des villes de livraison", "error": str(e)}), 500



@dashboard_bp.route("/livreurs/stats/chiffre-affaires", methods=["GET"])
@jwt_required()
@livreur_required
def route_chiffre_affaires_livreur():
    """
    Obtenir le chiffre d’affaires total d’un livreur
    ---
    tags:
      - Statistiques
      - Livreurs
    summary: Chiffre d’affaires total
    description: Cette route retourne le chiffre d’affaires total généré par le livreur connecté.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT du livreur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Chiffre d’affaires récupéré avec succès
        schema:
          type: object
          properties:
            livreur_id:
              type: string
              example: "64b8fae5e3b9ab9c8dbf8f67"
            chiffre_affaires_total:
              type: number
              format: float
              example: 1250000.50
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (non livreur)
      500:
        description: Erreur serveur lors de la récupération du chiffre d’affaires
    """
    livreur_id = get_jwt_identity()
    print("Livreur ID depuis le token :", livreur_id)
    try:
        result = get_chiffre_affaires_total_par_livreur(livreur_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": "Erreur lors de la récupération des villes de livraison", "error": str(e)}), 500


@dashboard_bp.route("/livreurs/stats/livraisons", methods=["GET"])
@jwt_required()
@livreur_required
def route_livraisons_total_livreur():
    """
    Obtenir le nombre total de livraisons avec évolution hebdomadaire
    ---
    tags:
      - Statistiques
      - Livreurs
    summary: Nombre total de livraisons et pourcentage d'évolution
    description: Cette route retourne le nombre total de livraisons effectuées par le livreur connecté ainsi que le pourcentage d'évolution par rapport à la semaine précédente.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT du livreur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Statistiques de livraison récupérées avec succès
        schema:
          type: object
          properties:
            livreur_id:
              type: string
              example: "64b8fae5e3b9ab9c8dbf8f67"
            nombre_livraisons_total:
              type: integer
              example: 150
            evolution_semaine:
              type: number
              format: float
              description: Pourcentage d'évolution par rapport à la semaine précédente (positif ou négatif)
              example: 12.5
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (non livreur)
      500:
        description: Erreur serveur lors de la récupération des statistiques
    """
    livreur_id = get_jwt_identity()

    result = get_nombre_livraisons_total_par_livreur(livreur_id)
    return jsonify(result), 200


@dashboard_bp.route("/livreurs/stats/produits", methods=["GET"])
@jwt_required()
@livreur_required
def route_produits_total_livreur():
    """
    Obtenir le nombre total de produits uniques livrés par le livreur
    ---
    tags:
      - Statistiques
      - Livreurs
    summary: Nombre total de produits uniques livrés
    description: Cette route retourne le nombre total de produits différents livrés par le livreur connecté.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT du livreur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Nombre total de produits uniques récupéré avec succès
        schema:
          type: object
          properties:
            livreur_id:
              type: string
              example: "64b8fae5e3b9ab9c8dbf8f67"
            nombre_produits_uniques:
              type: integer
              example: 45
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (non livreur)
      500:
        description: Erreur serveur lors de la récupération des données
    """
    livreur_id = get_jwt_identity()

    result = get_nombre_produits_uniques_par_livreur(livreur_id)
    return jsonify(result), 200



@dashboard_bp.route("/livreurs/stats/revenus-par-periode", methods=["GET"])
@jwt_required()
@livreur_required
def route_revenus_par_periode():
    """
    Obtenir le revenu total d’un livreur par période avec pagination temporelle
    ---
    tags:
      - Statistiques
      - Livreurs
    summary: Revenu total par période (jour, semaine, mois, année)
    description: >
      Cette route retourne le revenu total généré par le livreur connecté selon la granularité temporelle
      choisie (jour, semaine, mois, année). La navigation paginée permet de se déplacer entre les périodes :
      page=0 correspond à la période actuelle, -1 à la précédente, +1 à la suivante, etc.
      Le nombre de périodes par page est de 4, sauf pour la granularité "jour" où il est de 7.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT du livreur (format **Bearer &lt;token&gt;**)
        default: Bearer
      - name: granularite
        in: query
        type: string
        enum: [jour, semaine, mois, annee]
        required: false
        description: Granularité temporelle pour le revenu (jour, semaine, mois, année). Par defaut jour
        default: jour
      - name: page
        in: query
        type: integer
        required: false
        description: Numéro de page relative (0 = période actuelle, -1 = précédente, +1 = suivante)
        default: 0

    responses:
      200:
        description: Revenus récupérés avec succès pour la période demandée
        schema:
          type: object
          properties:
            granularite:
              type: string
              example: "mois"
            page:
              type: integer
              example: 0
            periodes:
              type: array
              description: Liste paginée des périodes avec revenus
              items:
                type: object
                properties:
                  periode:
                    type: string
                    example: "2025-07"  # format selon granularité
                  revenu:
                    type: number
                    format: float
                    example: 152300.75
      400:
        description: Paramètre(s) invalide(s)
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Granularité invalide"
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (non livreur)
      500:
        description: Erreur serveur lors de la récupération des revenus
    """
    livreur_id = get_jwt_identity()
    granularity = request.args.get("granularite", "jour")  # jour, semaine, mois, annee
    page = int(request.args.get("page", 0))  # page par défaut = 0

    try:
        data = get_revenus_par_periode_par_livreur(livreur_id, granularity, page)
        return jsonify(data), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400




@dashboard_bp.route("/livreurs/stats/paiements", methods=["GET"])
@jwt_required()
@livreur_required
def route_paiement_stat_livreur():
    """
    Obtenir les statistiques de paiement du livreur
    ---
    tags:
      - Statistiques
      - Livreurs
    summary: Statistiques des paiements reçus par le livreur
    description: Cette route retourne les statistiques de paiement associées au livreur connecté, telles que les montants totaux, les paiements reçus, en attente, etc.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT du livreur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Statistiques de paiement récupérées avec succès
        schema:
          type: object
          properties:
            livreur_id:
              type: string
              example: "64b8fae5e3b9ab9c8dbf8f67"
            montant_total:
              type: number
              format: float
              example: 145000.0
            montant_recu:
              type: number
              format: float
              example: 120000.0
            montant_non_recu:
              type: number
              format: float
              example: 25000.0
            nombre_transactions:
              type: integer
              example: 30
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (non livreur)
      500:
        description: Erreur serveur lors de la récupération des statistiques de paiement
    """
    livreur_id = get_jwt_identity()

    result = get_statistiques_paiement_par_livreur(livreur_id)
    return jsonify(result), 200



@dashboard_bp.route("/livreurs/stats/clients", methods=["GET"])
@jwt_required()
@livreur_required
def route_clients_stat_livreur():
    """
    Obtenir le nombre total de clients uniques servis par un livreur
    ---
    tags:
      - Statistiques
      - Livreurs
    summary: Nombre de clients uniques
    description: Cette route retourne le nombre total de clients différents ayant été livrés au moins une fois par le livreur connecté.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT du livreur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Nombre de clients uniques récupéré avec succès
        schema:
          type: object
          properties:
            livreur_id:
              type: string
              example: "64b8fae5e3b9ab9c8dbf8f67"
            nombre_clients_uniques:
              type: integer
              example: 32
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (non livreur)
      500:
        description: Erreur serveur lors de la récupération des données
    """
    livreur_id = get_jwt_identity()

    result = get_nombre_clients_uniques_par_livreur(livreur_id)
    return jsonify(result), 200




@dashboard_bp.route("/managers/stats/chiffre-affaires", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def route_chiffre_affaires_manager():
    """
    Obtenir le chiffre d'affaires total d'un manager
    ---
    tags:
      - Statistiques
      - Managers
    summary: Chiffre d'affaires total et variations
    description: >
      Cette route retourne le chiffre d'affaires total enregistré par le ou les magasins sous la responsabilité du manager connecté.
      Elle inclut également les variations par rapport à la période précédente (semaine/mois selon le contexte métier).

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT du manager (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Chiffre d'affaires récupéré avec succès
        schema:
          type: object
          properties:
            manager_id:
              type: string
              example: "64c9dd91fc13ae3a8e000001"
            chiffre_affaires_total:
              type: number
              format: float
              example: 2450000.0
            variation:
              type: number
              format: float
              description: Variation en pourcentage par rapport à la période précédente
              example: 8.75
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (réservé aux admins et managers)
      500:
        description: Erreur serveur lors de la récupération des données
    """
    manager_id = get_jwt_identity()
    try:
        result = get_chiffre_affaires_total()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": "Erreur lors de la récupération du chiffre d'affaires", "error": str(e)}), 500



# Retourne le nombre de livraisons total et les variations
@dashboard_bp.route("/managers/stats/livraisons", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def route_livraisons_total_manager():
    """
    Obtenir le nombre total de livraisons d’un manager
    ---
    tags:
      - Statistiques
      - Managers
    summary: Nombre total de livraisons et variations
    description: >
      Cette route retourne le nombre total de livraisons effectuées par les livreurs sous la supervision du manager connecté.
      Elle inclut également la variation par rapport à la période précédente (semaine, mois, etc.).

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT de l’utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Nombre de livraisons récupéré avec succès
        schema:
          type: object
          properties:
            manager_id:
              type: string
              example: "64c9dd91fc13ae3a8e000001"
            nombre_livraisons_total:
              type: integer
              example: 320
            variation:
              type: number
              format: float
              description: Variation en pourcentage par rapport à la période précédente
              example: -4.25
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (réservé à admin et manager)
      500:
        description: Erreur serveur lors de la récupération du nombre de livraisons
    """
    manager_id = get_jwt_identity()
    try:
        result = get_nombre_livraisons_total()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": "Erreur lors de la récupération du nombre de livraisons", "error": str(e)}), 500


@dashboard_bp.route("/managers/stats/clients", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def route_clients_total_manager():
    """
    Obtenir le nombre total de clients d’un manager
    ---
    tags:
      - Statistiques
      - Managers
    summary: Nombre total de clients et variation
    description: >
      Cette route retourne le nombre total de clients associés aux magasins gérés par le manager connecté.
      Elle inclut aussi la variation du nombre de clients par rapport à la période précédente (ex. : semaine ou mois).

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT de l’utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Nombre total de clients récupéré avec succès
        schema:
          type: object
          properties:
            manager_id:
              type: string
              example: "64c9dd91fc13ae3a8e000001"
            nombre_clients_total:
              type: integer
              example: 214
            variation:
              type: number
              format: float
              description: Variation en pourcentage par rapport à la période précédente
              example: 5.6
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (réservé à admin et manager)
      500:
        description: Erreur serveur lors de la récupération du nombre de clients
    """
    manager_id = get_jwt_identity()
    try:
        result = get_nombre_clients_total_livre()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": "Erreur lors de la récupération du nombre de clients", "error": str(e)}), 500



# Retourne le nombre de produits total et les variations
@dashboard_bp.route("/managers/stats/produits", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def route_produits_total_manager():
    """
    Obtenir le nombre total de produits livrés sous la supervision du manager
    ---
    tags:
      - Statistiques
      - Managers
    summary: Nombre total de produits livrés et variation
    description: >
      Cette route retourne le nombre total de produits livrés par les livreurs rattachés aux magasins du manager connecté.
      Elle inclut également le pourcentage d’évolution du nombre de produits par rapport à la période précédente (ex. : semaine ou mois).

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT de l’utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Nombre total de produits livrés récupéré avec succès
        schema:
          type: object
          properties:
            manager_id:
              type: string
              example: "64c9dd91fc13ae3a8e000001"
            nombre_produits_total:
              type: integer
              example: 840
            variation:
              type: number
              format: float
              description: Variation en pourcentage par rapport à la période précédente
              example: 3.8
    
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (réservé à admin et manager)
      500:
        description: Erreur serveur lors de la récupération du nombre de clients
    """

    manager_id = get_jwt_identity()
    try:
        result = get_nombre_produits_livres()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": "Erreur lors de la récupération du nombre de produits", "error": str(e)}), 500
    
    
    
@dashboard_bp.route("/managers/stats/paiements", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def route_paiement_stat_total():
    """
    Obtenir les statistiques de paiement globales des magasins du manager
    ---
    tags:
      - Statistiques
      - Managers
    summary: Statistiques de paiement globales
    description: >
      Cette route retourne les statistiques de paiement globales relatives aux ventes effectuées par les livreurs et magasins
      sous la supervision du manager connecté. Cela inclut le montant total perçu, les paiements en attente, les transactions, etc.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT de l’utilisateur (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Statistiques de paiement récupérées avec succès
        schema:
          type: object
          properties:
            manager_id:
              type: string
              example: "64c9dd91fc13ae3a8e000001"
            montant_total:
              type: number
              format: float
              example: 850000.0
            montant_recu:
              type: number
              format: float
              example: 720000.0
            montant_non_recu:
              type: number
              format: float
              example: 130000.0
            nombre_transactions:
              type: integer
              example: 57
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (réservé à admin et manager)
      500:
        description: Erreur serveur lors de la récupération des statistiques de paiement
    """
    result = get_statistiques_paiement_total()
    return jsonify(result), 200



@dashboard_bp.route("/managers/stats/revenus-par-periode", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def route_revenus_par_periode_total():
    """
    Obtenir les revenus par période, les variations et la liste des livreurs
    ---
    tags:
      - Statistiques
      - Managers
    summary: Revenus par période (manager ou livreur)
    description: >
      Cette route retourne :
        - Les revenus totaux du manager (ou d’un livreur si précisé) par période (jour, semaine, mois ou année)
        - La variation entre la dernière et l’avant-dernière période
        - La liste complète des livreurs rattachés aux magasins du manager

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT (format **Bearer &lt;token&gt;**)
        default: Bearer
      - in: query
        name: granularite
        type: string
        required: false
        description: Niveau de regroupement temporel (**jour**, **semaine**, **mois**, **annee**)
        enum: [jour, semaine, mois, annee]
        default: jour
      - in: query
        name: livreur_id
        type: string
        required: false
        description: ID du livreur ciblé (optionnel)
      - in: query
        name: page
        type: integer
        required: false
        default: 0
        description: Période temporelle relative (0 = période actuelle, -1 = précédente)

    responses:
      200:
        description: Revenu par période récupéré avec succès
        schema:
          type: object
          properties:
            revenus:
              type: object
              properties:
                periode:
                  type: string
                  example: "2025-W28"
                montant_total:
                  type: number
                  format: float
                  example: 154000.0
                variation:
                  type: number
                  format: float
                  description: Pourcentage par rapport à la période précédente
                  example: 7.25
                historique:
                  type: array
                  items:
                    type: object
                    properties:
                      label:
                        type: string
                        example: "2025-W26"
                      montant:
                        type: number
                        format: float
                        example: 142000.0
            livreurs:
              type: array
              description: Liste des livreurs rattachés au manager
              items:
                type: object
                properties:
                  id:
                    type: string
                    example: "64c9dd91fc13ae3a8e000003"
                  nom:
                    type: string
                    example: "Mohamed DIALLO"
      400:
        description: Requête invalide (ex.  granularité incorrecte)
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé
      500:
        description: Erreur serveur lors de la récupération des revenus
    """
    from services.user_service import get_livreur_service

    granularity = request.args.get("granularite", "jour")
    livreur_id = request.args.get("livreur_id", None)
    page = int(request.args.get("page", 0))

    try:
        revenus_data = get_revenus_par_periode_total(livreur_id, granularity, page)

        livreur_result = get_livreur_service()
        if livreur_result["status"] != 200:
            raise Exception("Impossible de récupérer les livreurs")

        return jsonify({
            "revenus": revenus_data,
            "livreurs": livreur_result["livreurs"]
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erreur interne : {str(e)}"}), 500



@dashboard_bp.route("/managers/villes_livraison", methods=["GET"])
@jwt_required()
@role_required("manager", "admin")
def villes_livraison_total():
    """
    Obtenir les zones de livraison maximales des magasins du manager
    ---
    tags:
      - Statistiques
      - Managers
    summary: Villes de livraison maximales
    description: >
      Cette route retourne toutes les zones (villes ou quartiers) couvertes par les livraisons effectuées à travers les magasins supervisés
      par le manager connecté (ou l'admin). Elle peut servir à des fins d’analyse de couverture géographique.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Villes de livraison récupérées avec succès
        schema:
          type: object
          properties:
            villes:
              type: array
              description: Liste des villes où des livraisons ont été effectuées
              items:
                type: string
              example: ["Yaoundé", "Douala", "Bafoussam", "Garoua"]
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé (réservé à admin et manager)
      500:
        description: Erreur serveur lors de la récupération des villes
    """
    try:
        result = get_villes_livraison_total()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": "Erreur lors de la récupération des villes de livraison", "error": str(e)}), 500


# Retourne tous les produits du stock livreur avec les catégories
@dashboard_bp.route("/managers/stock_par_categorie", methods=["GET"])
@role_required("admin", "manager")
def get_stock_magasin_par_categorie():
    """
    Obtenir le stock total par catégorie pour les magasins du manager
    ---
    tags:
      - Statistiques
      - Managers
    summary: Stock total par catégorie
    description: >
      Cette route retourne le stock agrégé de produits par catégorie, 
      pour tous les magasins rattachés au manager connecté ou à l'administrateur.
      Elle permet de suivre l’état du stock organisé par type de produit.

    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Jeton JWT (format **Bearer &lt;token&gt;**)
        default: Bearer

    responses:
      200:
        description: Stock par catégorie récupéré avec succès
        schema:
          type: object
          properties:
            categories:
              type: array
              items:
                type: object
                properties:
                  categorie:
                    type: string
                    example: "Boissons"
                  total_quantite:
                    type: integer
                    example: 1200
                  unite:
                    type: string
                    example: "bouteilles"
      401:
        description: Non autorisé – Jeton manquant ou invalide
      403:
        description: Accès refusé – Rôle non autorisé
      500:
        description: Erreur lors de la récupération des données de stock
    """
    data = {}
    data['admin_id'] = get_jwt_identity() 
    data = inject_magasin_id(data)
    try:
        result = get_stock_par_categorie_total(data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": "Erreur lors de la récupération du stock", "error": str(e)}), 500
