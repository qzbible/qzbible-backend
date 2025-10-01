# services/notification_service.py 
from models.notification_model import NotificationModel 
from models.user_model import UserModel
from models.client_model import ClientModel

# notifier_manager_ristourne(result.inserted_id,  livraison["client_id"], livraison["montant_total"], livraison["montant_paye"], livraison["ristourne"], livraison["action_manager"])




def notifier_manager_ristourne(livraison_id, client_id, livreur_id , montant_total, montant_paye, ristourne, date_livraison):
    # Récupérer les nom du clients et du livreur
    client_data = ClientModel.get_client_by_id(client_id)
    if client_data:
        client_data.pop("_id", None)  # Supprimer l'ID
    # extraire juste le nom du client
    nom_client = client_data.get("name", "") + " " + client_data.get("first_name", "") if client_data else ""

    livreur_data = UserModel.get_user_by_id(livreur_id)
    
    # extraire juste le nom du livreur
    nom_livreur = livreur_data.get("name", "") + " " + livreur_data.get("first_name", "") if livreur_data else ""
    
    client_data = ClientModel.get_client_by_id(client_id)
    
    nom_client = client_data.get("nom", "") 
    
    NotificationModel.create_notification({
        "title": "Livraison avec ristourne",
        "message": f"Une livraison avec ristourne a été effectuée le {date_livraison} par le livreur nommé {nom_livreur} au client {nom_client}. Montant total : {montant_total}, montant payé : {montant_paye} , ristourne : {ristourne}. Bien vouloir valider ou rejeter le montant de la livraison ID : {livraison_id}",
        "type": "info",
        "lien": f"/livraisons/{livraison_id}",
    })