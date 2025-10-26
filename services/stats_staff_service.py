from collections import defaultdict
from datetime import datetime, timedelta, date
 
from models.user_model import UserModel
 
from models.church_model import ChurchModel

from models.connexion_model import ConnexionModel
 
import os
from werkzeug.utils import secure_filename
from flask import current_app
from models.image_staff_model import ImageStaffModel
from flask import request



 
# Retourne les utilisateurs récemment connnectés

def get_utilisateurs_recents_connectes_service(limit=10):
    """
    Retourne les derniers utilisateurs connectés avec leur email, rôle, magasin, date et IP de connexion.
    """

    connexions = ConnexionModel.collection.find().sort("timestamp", -1).limit(limit)
    resultats = []

    for connexion in connexions:
        user_id = connexion.get("user_id")
        utilisateur = UserModel.find_by_id(user_id) if user_id else None

        item = {
            "email": connexion.get("email", ""),
            "role": connexion.get("role", ""),
            "date_connexion": connexion.get("timestamp"),
            "ip": connexion.get("ip_address", "")
        }

        if utilisateur:
            item["nom_complet"] = utilisateur.get("first_name", "") + " " + utilisateur.get("last_name", "")

        # Ajouter magasin si applicable
        magasin_id = connexion.get("magasin_id")
        if magasin_id:
            magasin = ChurchModel.get_church_by_id(magasin_id)
            if magasin:
                item["magasin"] = {
                    "id": str(magasin["_id"]),
                    "denomination": magasin.get("denomination", "")
                }

        resultats.append(item)

    return {
        "utilisateurs_recents_connectes": resultats,
        "total": len(resultats)
    }

 


# premier compartiment pour les statistiques de staff
def get_nombre_churchs_total():
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    start_date = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
    end_date = today
    periode_duree = end_date - start_date

    previous_start = start_date - periode_duree
    previous_end = start_date

    # Magasins créés cette semaine et la précédente
    current = list(ChurchModel.collection.find({"created_at": {"$gte": start_date, "$lt": end_date}}))
    previous = list(ChurchModel.collection.find({"created_at": {"$gte": previous_start, "$lt": previous_end}}))

    total = ChurchModel.collection.count_documents({})

    variation = 0.0
    if len(previous) == 0:
        variation = 100.0 if len(current) > 0 else 0.0
    else:
        variation = ((len(current) - len(previous)) / len(previous)) * 100

    return {
        "valeur": total,
        "variation_percent": round(variation, 2),
        "periode": {
            "debut": start_date.isoformat(),
            "fin": end_date.isoformat()
        }
    }


# nombre d'admin ou manager total
def get_nombre_admins_churchs_total():
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    start_date = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
    end_date = today
    periode_duree = end_date - start_date

    previous_start = start_date - periode_duree
    previous_end = start_date

    current = list(UserModel.collection.find({
        "role": {"$in": ["admin", "manager"]},
        "created_at": {"$gte": start_date, "$lt": end_date}
    }))
    previous = list(UserModel.collection.find({
        "role": {"$in": ["admin", "manager"]},
        "created_at": {"$gte": previous_start, "$lt": previous_end}
    }))

    total = UserModel.collection.count_documents({"role": {"$in": ["admin", "manager"]}})

    variation = 0.0
    if len(previous) == 0:
        variation = 100.0 if len(current) > 0 else 0.0
    else:
        variation = ((len(current) - len(previous)) / len(previous)) * 100

    return {
        "valeur": total,
        "variation_percent": round(variation, 2),
        "periode": {
            "debut": start_date.isoformat(),
            "fin": end_date.isoformat()
        }
    }

  



def ajouter_image_service(data, file):
    filename = secure_filename(file.filename)
    upload_path = current_app.config["STAFF_IMAGE_FOLDER"]
    os.makedirs(upload_path, exist_ok=True)

    path = os.path.join(upload_path, filename)
    file.save(path)

    # Enregistrement en base de données (optionnel mais recommandé)
    image_data = {
        "nom": data.get("nom", filename),
        "description": data.get("description", ""),
        "categorie": data.get("categorie", ""),
        "filename": filename,
        "tags": data.get("tags", []),
        "created_at": datetime.utcnow()
    }

    result = ImageStaffModel.ajouter_image(image_data)

    return {
        "message": "Image ajoutée avec succès.",
        "image_id": result,
        "filename": filename
    }, 201

    
 