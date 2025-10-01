# services/commande_service.py

from models.commande_model import CommandeModel
from datetime import datetime

def create_commande_service(data):
    """Créer une nouvelle commande"""
    return CommandeModel.create_commande(data)

def get_all_commandes_service():
    """Récupérer toutes les commandes"""
    return CommandeModel.get_all_commandes()

def get_commande_by_id_service(commande_id):
    """Récupérer une commande par son ID"""
    return CommandeModel.get_commande_by_id(commande_id)

def get_commandes_by_client_service(client_id):
    """Récupérer toutes les commandes d’un client"""
    return CommandeModel.get_commandes_by_client(client_id)

def get_commandes_by_magasin_service(magasin_id):
    """Récupérer toutes les commandes d’un magasin"""
    return CommandeModel.get_commandes_by_magasin(magasin_id)

def update_commande_service(commande_id, data):
    """Mettre à jour une commande"""
    return CommandeModel.update_commande(commande_id, data)

def delete_commande_service(commande_id):
    """Supprimer une commande"""
    return CommandeModel.delete_commande(commande_id)
