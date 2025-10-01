# tests/integration/test_livraison_routes.py

import pytest
from flask import json
from bson import ObjectId
from datetime import datetime, timedelta
from extensions import mongo
from models.user_model import UserModel
from models.client_model import ClientModel
from models.produit_model import ProduitModel
from models.stock_livreur_model import StockLivreurModel

from utils.jwt_token import generate_token  # JWT utilitaire

@pytest.fixture
def setup_livreur_and_client(app):
    with app.app_context():
        magasin_id = "662c0cbf6b5a4a1f25facc22"

        # Création du livreur
        livreur_id = UserModel.create_livreur(
            name="Jean",
            first_name="Paul",
            email="jean.paul@test.com",
            password="password",
            magasin_id=magasin_id
        )

        # Création manuelle du client
        client_doc = {
            "nom": "Client Test",
            "created_by": None,
            "telephone": "690000000",
            "email": "client@test.com",
            "ville": "Douala",
            "quartier": "Bonapriso",
            "photo_profil": None,
            "magasin_id": ObjectId(magasin_id),
            "created_at": datetime.utcnow()
        }
        result = ClientModel.get_collection().insert_one(client_doc)
        client_id = str(result.inserted_id)

        # Création d'une catégorie fictive
        categorie_doc = {
            "nom": "Catégorie Test",
            "description": "Test catégorie",
            "magasin_id": ObjectId(magasin_id),
            "created_at": datetime.utcnow()
        }
        result_cat = mongo.db.categories.insert_one(categorie_doc)
        categorie_id = result_cat.inserted_id

        # Création d’un produit
        produit_id = ProduitModel.create_produit({
            "nom": "Produit Test",
            "prix": 1000,
            "quantite": 100,
            "unite": "pièce",
            "categorie_id": categorie_id,
            "magasin_id": ObjectId(magasin_id)
        })

        # Ajout au stock du livreur
        StockLivreurModel.ajouter_stock(livreur_id, [{
            "produit_id": produit_id,
            "quantite": 20
        }])

        return {
            "livreur_id": livreur_id,
            "client_id": client_id,
            "produit_id": produit_id,
            "magasin_id": magasin_id
        }


def test_creer_livraison_integration(client, setup_livreur_and_client):
    """
    Test d'intégration complet de la route POST /livraisons
    """
    # Récupération des IDs
    data_setup = setup_livreur_and_client
    livreur_id = data_setup["livreur_id"]
    client_id = data_setup["client_id"]
    produit_id = data_setup["produit_id"]

    # Générer un JWT valide
    token = generate_token(user_id=livreur_id, role="livreur")

    # Construire le payload
    payload = {
        "client_id": str(client_id),
        "produits": [
            {
                "produit_id": str(produit_id),
                "quantite": 2,
                "prix": 1000
            }
        ],
        "statut_paiement": "payé",
        "magasin_id": "662c0cbf6b5a4a1f25facc22",
        "date_commande": datetime.utcnow().isoformat(),
        "date_livraison": (datetime.utcnow() + timedelta(days=1)).isoformat()
    }

    # Envoi de la requête
    response = client.post(
        "/livraisons",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    # Vérification de la réponse
    assert response.status_code == 201
    data = response.get_json()
    print("\n[DEBUG] Réponse de /livraisons:", data)
    assert "livraison_id" in data
