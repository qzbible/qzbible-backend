"""
| Nom du test                           | Ce qu'on vérifie                         |
| ------------------------------------- | ---------------------------------------- |
| `test_livraison_donnees_invalides()`  | Données invalides rejetées par le schéma |
| `test_livraison_produit_inexistant()` | Produit non trouvé → erreur 404          |
| `test_livraison_succes()`             | Livraison créée avec stock suffisant     |
| `test_livraison_succes_conditionnement()` | Livraison avec conditionnement réussi|
| `test_livraison_succes_manager()`     | Livraison créée par un manager
|
| Commande d'exécution : pytest tests/unit/test_livraison_creation.py --disable-warnings -v
"""

import pytest
from services.livraison_service import creer_livraison

from unittest.mock import patch
from bson import ObjectId


def test_livraison_donnees_invalides():
    """
    Teste si la validation échoue avec des données incomplètes ou invalides.
    """
    data = {
        "client_id": "abc123",  # Trop court
        "produits": [],
        "statut_paiement": "invalide",
        "magasin_id": "xyz"
    }
    response, status = creer_livraison(data)
    assert status == 400
    assert "error" in response


@patch("services.livraison_service.ProduitModel.get_by_id")
def test_livraison_produit_inexistant(mock_get_by_id):
    """
    Teste si la livraison échoue quand un produit n'existe pas.
    """
    mock_get_by_id.return_value = None  # simulate produit introuvable
    data = {
        "client_id": "5f43a9fc6e8b4b1c2a7f1234",
        "livreur_id": "5f43a9fc6e8b4b1c2a7f5678",
        "produits": [
            {"produit_id": "5f43a9fc6e8b4b1c2a7f9999", "quantite": 2}
        ],
        "statut_paiement": "payé",
        "magasin_id": "5f43a9fc6e8b4b1c2a7fabcd"
    }
    response, status = creer_livraison(data)
    assert status == 404
    assert "Produit" in response["error"]


@patch("services.livraison_service.ProduitModel.get_by_id")
@patch("services.livraison_service.StockLivreurModel.get_stock_livreur")
@patch("services.livraison_service.LivraisonModel.create_livraison")
@patch("services.livraison_service.StockLivreurModel.retirer_stock")
def test_livraison_succes(mock_retirer, mock_create, mock_get_stock, mock_get_produit):
    """
    Teste un scénario de livraison réussi.
    """
    produit_id = "5f43a9fc6e8b4b1c2a7f9999"

    # Simule le produit existant
    mock_get_produit.return_value = {
        "_id": ObjectId(produit_id),
        "nom": "Savon",
        "prix": 1000
    }

    # Simule un stock suffisant
    mock_get_stock.return_value = [
        {"produit_id": ObjectId(produit_id), "quantite": 10}
    ]

    # Simule l'ID de livraison retourné
    mock_create.return_value = "livraison123"

    data = {
        "client_id": "5f43a9fc6e8b4b1c2a7f1234",
        "livreur_id": "5f43a9fc6e8b4b1c2a7f5678",
        "produits": [
            {"produit_id": produit_id, "quantite": 2}
        ],
        "statut_paiement": "payé",
        "magasin_id": "5f43a9fc6e8b4b1c2a7fabcd"
    }

    response, status = creer_livraison(data)
    assert status == 201
    assert response["livraison_id"] == "livraison123"

    # Vérifie que le stock est bien retiré
    mock_retirer.assert_called_once()


def test_livraison_conditionnement_inexistant(monkeypatch, client, clear_db):
    """
    Vérifie que la livraison échoue si le conditionnement est invalide.
    """
    # Mock ProduitModel.get_by_id pour retourner un produit factice
    def mock_get_by_id(pid):
        return {"_id": pid, "nom": "Produit A", "prix": 100}

    # Mock ProduitModel.get_conditionnement_by_id pour retourner None (conditionnement introuvable)
    def mock_get_conditionnement_by_id(pid, cid):
        return None

    # Mock StockLivreurModel.get_stock_livreur pour retourner du stock fictif
    def mock_get_stock_livreur(livreur_id):
        return [{"produit_id": "abc123", "quantite": 50}]

    monkeypatch.setattr("services.livraison_service.ProduitModel.get_by_id", mock_get_by_id)
    monkeypatch.setattr("services.livraison_service.ProduitModel.get_conditionnement_by_id", mock_get_conditionnement_by_id)
    monkeypatch.setattr("services.livraison_service.StockLivreurModel.get_stock_livreur", mock_get_stock_livreur)

    # Données de test avec un conditionnement invalide
    data = {
        "client_id": "5f4dcc3b5aa765d61d8327de",
        "livreur_id": "5f4dcc3b5aa765d61d8327df",
        "produits": [
            {
                "produit_id": "abc123",
                "conditionnement_id": "cond999",  # Inexistant
                "quantite_conditionnement": 2
            }
        ],
        "statut_paiement": "payé",
        "magasin_id": "5f4dcc3b5aa765d61d8327da"
    }

    from services.livraison_service import creer_livraison
    response, status_code = creer_livraison(data)

    assert status_code == 404
    assert "Conditionnement introuvable" in response["error"]
