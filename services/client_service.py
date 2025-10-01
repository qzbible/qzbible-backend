from werkzeug.utils import secure_filename
from flask import current_app
import os
from bson import ObjectId
from models.client_model import ClientModel
from models.livraison_model import LivraisonModel
from models.user_model import UserModel
from utils.re import clean_string

def create_client_service(data, photo_file=None):
    photo_filename = None
    if photo_file:
        filename = secure_filename(photo_file.filename)
        image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        photo_file.save(image_path)
        photo_filename = filename

    data["photo_profil"] = photo_filename
    # Vérifie si un client existe déjà avec le même numéro de téléphone et nom et ville et quartier
    existing_client = ClientModel.get_client_by_phone(data["telephone"])
    # Verification du nom
    if existing_client and existing_client["nom"] == data["nom"] and existing_client["ville"] == data["ville"] and existing_client["quartier"] == data["quartier"]:
        return {"message": "Un client avec ce numéro de téléphone, nom, ville et quartier existe déjà"}, 400

    client_id = ClientModel.create_client(data)
    return {"message": "Client créé", "client_id": client_id}, 201



# Récupérer tous les clients d'un magasin
def get_all_clients_service(magasin_id):
    # Si magasin_id est un dict de type {"$oid": "..."} on extrait l'ID
    if isinstance(magasin_id, dict) and "$oid" in magasin_id:
        magasin_id = magasin_id["$oid"]
        
    clients = ClientModel.get_all_clients(magasin_id)
    for c in clients:
        c["_id"] = str(c["_id"])
    return clients




def get_client_by_id_service(client_id):
    client = ClientModel.get_client_by_id(client_id)
    if client:
        client["_id"] = str(client["_id"])
    return client



def update_client_service(client_id, data):
    return ClientModel.update_client(client_id, data)



def delete_client_service(client_id):
    return ClientModel.delete_client(client_id)



# Récupérer tous les clients d'un livreur avec pour chacun le nombre de livraison concernant chaque client
# Et le montant total de chaque livraison pour chaque client

def get_clients_livreur(livreur_id):
    """
    Récupère tous les clients ayant reçu au moins une livraison de ce livreur,
    avec le nombre total de livraisons et le montant cumulé pour chacun.
    """
    # 1. Récupération de toutes les livraisons faites par le livreur
    livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)

    # 2. Agréger les livraisons par client_id
    stats = {}

    for livraison in livraisons:
        client_id = str(livraison["client_id"])  # ID client sous forme de string

        if client_id not in stats:
            stats[client_id] = {
                "client_id": client_id,
                "nombre_livraisons": 0,
                "montant_total": 0,
            }

        stats[client_id]["nombre_livraisons"] += 1
        stats[client_id]["montant_total"] += livraison.get("montant_total", 0)

    # 3. Récupérer les infos clients une seule fois
    client_ids = list(stats.keys())
    clients_info = ClientModel.get_clients_by_ids(client_ids)

    # 4. Fusionner les infos client avec les stats
    for client in clients_info:
        cid = str(client["_id"])
        if cid in stats:
            stats[cid]["nom"] = client.get("nom", "")
            stats[cid]["telephone"] = client.get("telephone", "")
            stats[cid]['quartier'] = client.get("quartier", "")
            stats[cid]['ville'] = client.get("ville", "")
            

    return list(stats.values())



# Fonction statistiques 
# Récupérer les meilleurs clients d'un livreur avec le montant total de chaque livraison pour chaque client

def get_meilleurs_clients_livreur(livreur_id):
    """
    Retourne les meilleurs clients d’un livreur donné,
    triés par montant total décroissant.
    """
    # 1. Récupération de toutes les livraisons faites par le livreur
    livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)

    # 2. Agrégation des données par client
    stats = {}

    for livraison in livraisons:
        client_id = str(livraison["client_id"])

        if client_id not in stats:
            stats[client_id] = {
                "client_id": client_id,
                "nombre_livraisons": 0,
                "montant_total": 0,
            }

        stats[client_id]["nombre_livraisons"] += 1
        stats[client_id]["montant_total"] += livraison.get("montant_total", 0)

    # 3. Récupération des infos clients
    client_ids = list(stats.keys())
    clients_info = ClientModel.get_clients_by_ids(client_ids)

    # 4. Fusionner les infos clients
    for client in clients_info:
        cid = str(client["_id"])
        if cid in stats:
            stats[cid]["nom"] = clean_string(client.get("nom", ""))
            stats[cid]["telephone"] = client.get("telephone", "")
            stats[cid]["quartier"] = client.get("quartier", "")
            stats[cid]["ville"] = client.get("ville", "")

    # 5. Retourner trié selon montant_total (décroissant)
    return sorted(stats.values(), key=lambda x: x["montant_total"], reverse=True)[:5]




def get_meilleurs_clients_total():
    """
    Retourne les meilleurs clients de tous le magasin,
    triés par montant total décroissant.
    """
    # 1. Récupération de toutes les livraisons faites par le livreur
    livraisons = LivraisonModel.get_all_livraisons()

    # 2. Agrégation des données par client
    stats = {}

    for livraison in livraisons:
        client_id = str(livraison["client_id"])

        if client_id not in stats:
            stats[client_id] = {
                "client_id": client_id,
                "nombre_livraisons": 0,
                "montant_total": 0,
            }

        stats[client_id]["nombre_livraisons"] += 1
        stats[client_id]["montant_total"] += livraison.get("montant_total", 0)

    # 3. Récupération des infos clients
    client_ids = list(stats.keys())
    clients_info = ClientModel.get_clients_by_ids(client_ids)

    # 4. Fusionner les infos clients
    for client in clients_info:
        cid = str(client["_id"])
        if cid in stats:
            stats[cid]["nom"] = client.get("nom", "")
            stats[cid]["telephone"] = client.get("telephone", "")
            stats[cid]["quartier"] = client.get("quartier", "")
            stats[cid]["ville"] = client.get("ville", "")

    # 5. Retourner trié selon montant_total (décroissant)
    return sorted(stats.values(), key=lambda x: x["montant_total"], reverse=True)[:5]


# Récupérer tous les clients d'un magasin avec pour chacun le nombre de livraison concernant chaque client
def get_clients_magasins(filters=None):
    livraisons = LivraisonModel.get_all_livraisons()

    stats = {}
    for livraison in livraisons:
        client_id = str(livraison["client_id"])
        if client_id not in stats:
            stats[client_id] = {
                "client_id": client_id,
                "nombre_livraisons": 0,
                "montant_total": 0,
            }
        stats[client_id]["nombre_livraisons"] += 1
        stats[client_id]["montant_total"] += livraison.get("montant_total", 0)

    client_ids = list(stats.keys())
    clients_info = ClientModel.get_clients_by_ids(client_ids)

    created_by_ids = list({
        str(client.get("created_by"))
        for client in clients_info
        if client.get("created_by") is not None
    })
    users = UserModel.collection.find(
        {"_id": {"$in": [ObjectId(uid) for uid in created_by_ids]}}
    )
    user_map = {str(user["_id"]): user for user in users}

    result = []
    for client in clients_info:
        cid = str(client["_id"])
        if cid in stats:
            stats[cid].update({
                "nom": clean_string(client.get("nom", "")),
                "telephone": client.get("telephone", ""),
                "quartier": client.get("quartier", ""),
                "ville": client.get("ville", ""),
                "photo_profil": client.get("photo_profil", None),
                "created_by": str(client.get("created_by", "")),
                "created_by_name": "",
                "created_by_first_name": "",
                "created_at": client.get("created_at")
            })

            creator_id = str(client.get("created_by", ""))
            if creator_id and creator_id in user_map:
                stats[cid]["created_by_name"] = user_map[creator_id].get("name", "")
                stats[cid]["created_by_first_name"] = user_map[creator_id].get("first_name", "")

            result.append(stats[cid])

    # Filtres
    if filters:
        def match_filter(c):
            if filters["nom"] and filters["nom"].lower() not in c["nom"].lower():
                return False
            if filters["telephone"] and filters["telephone"] not in c["telephone"]:
                return False
            if filters["quartier"] and filters["quartier"].lower() not in c["quartier"].lower():
                return False
            if filters["ville"] and filters["ville"].lower() not in c["ville"].lower():
                return False
            if filters["created_by_name"] and filters["created_by_name"].lower() not in c["created_by_name"].lower():
                return False
            return True

        result = list(filter(match_filter, result))

    # Tri par date de création décroissant
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return result
