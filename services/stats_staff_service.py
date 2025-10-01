from collections import defaultdict
from datetime import datetime, timedelta, date
from models.livraison_model import LivraisonModel
from models.user_model import UserModel
from models.magasin_model import MagasinModel
from models.connexion_model import ConnexionModel
from utils.dates import get_week_date_range
from models.client_model import ClientModel
from dateutil.relativedelta import relativedelta
import os
from werkzeug.utils import secure_filename
from flask import current_app
from models.image_staff_model import ImageStaffModel
from flask import request





def get_stats_utilisation_globale(granularite='semaine', page=0):    
    """
    Retourne les statistiques globales d'utilisation de la plateforme :
    - Nombre de connexions
    - Nombre de livraisons
    - Nombre de produits livrés
    - Nombre de magasins actifs
    - Nombre d'utilisateurs actifs
    - Taux de croissance entre la dernière période et la précédente
    """
    connexions = ConnexionModel.get_all()
    livraisons = LivraisonModel.get_all_livraisons_plateforme()
    utilisateurs = UserModel.get_all_users()
    magasins = MagasinModel.get_all_magasin()

    def get_key(date_obj):
        if granularite == "jour":
            return date_obj.strftime("%Y-%m-%d")
        elif granularite == "semaine":
            iso_year, iso_week, _ = date_obj.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        elif granularite == "mois":
            return f"{date_obj.year}-{date_obj.month:02d}"
        elif granularite == "annee":
            return str(date_obj.year)
        else:
            raise ValueError("Granularité invalide")

    def get_periods(granularite, page):
        now = date.today()
        periodes = []

        if granularite == "jour":
            current_monday = now - timedelta(days=now.weekday())
            start = current_monday + timedelta(weeks=page)
            for i in range(7):
                day = start + timedelta(days=i)
                key = day.strftime("%Y-%m-%d")
                periodes.append((key, day, day))

        elif granularite == "semaine":
            current_year, current_week, _ = now.isocalendar()
            start_week = current_week + (page * 4)
            year = current_year
            for i in range(4):
                week = start_week + i
                while week > 52:
                    week -= 52
                    year += 1
                while week < 1:
                    week += 52
                    year -= 1
                first = date.fromisocalendar(year, week, 1)
                last = first + timedelta(days=6)
                key = f"{year}-W{week:02d}"
                periodes.append((key, first, last))

        elif granularite == "mois":
            base = now.replace(day=1) + relativedelta(months=page * 4)
            for i in range(4):
                d = base + relativedelta(months=i)
                key = f"{d.year}-{d.month:02d}"
                start = d
                end = (d + relativedelta(months=1)) - timedelta(days=1)
                periodes.append((key, start, end))

        elif granularite == "annee":
            start_year = now.year + (page * 4)
            for i in range(4):
                y = start_year + i
                key = str(y)
                start = date(y, 1, 1)
                end = date(y, 12, 31)
                periodes.append((key, start, end))

        return periodes

    # Regroupement
    connexions_par_periode = defaultdict(int)
    livraisons_par_periode = defaultdict(int)
    produits_par_periode = defaultdict(int)

    for c in connexions:
        date_obj = c.get("timestamp")
        if date_obj:
            key = get_key(date_obj)
            connexions_par_periode[key] += 1

    for l in livraisons:
        date_obj = l.get("created_at")
        if date_obj:
            key = get_key(date_obj)
            livraisons_par_periode[key] += 1
            produits = l.get("produits", [])
            produits_par_periode[key] += sum(p.get("quantite", 0) for p in produits)

    # Génération des périodes affichées
    periodes = get_periods(granularite, page)
    now = date.today()

    connexions_sorted = []
    livraisons_sorted = []
    produits_sorted = []

    for key, start, end in periodes:
        connexions_sorted.append({
            "date": key,
            "count": connexions_par_periode.get(key, 0),
            "debut": str(start),
            "fin": str(end),
            "incomplet": end > now and connexions_par_periode.get(key, 0) == 0
        })
        livraisons_sorted.append({
            "date": key,
            "count": livraisons_par_periode.get(key, 0),
            "debut": str(start),
            "fin": str(end),
            "incomplet": end > now and livraisons_par_periode.get(key, 0) == 0
        })
        produits_sorted.append({
            "date": key,
            "count": produits_par_periode.get(key, 0),
            "debut": str(start),
            "fin": str(end),
            "incomplet": end > now and produits_par_periode.get(key, 0) == 0
        })

    # Variation
    def compute_variation(sorted_list):
        if len(sorted_list) < 2:
            return 0.0
        val_prec = sorted_list[-2]["count"]
        val_cour = sorted_list[-1]["count"]
        if val_prec == 0:
            return 100.0 if val_cour > 0 else 0.0
        return ((val_cour - val_prec) / val_prec) * 100

    # Utilisateurs/magasins actifs pour la dernière période du bloc affiché
    current_key = periodes[-1][0]
    utilisateurs_actifs = len({u["_id"] for u in utilisateurs if get_key(u.get("last_login", now)) == current_key})
    magasins_actifs = len({m["_id"] for m in magasins if get_key(m.get("last_activity", now)) == current_key})

    return {
        "periode": granularite,
        "page": page,
        "growth_rate": {
            "connexions": round(compute_variation(connexions_sorted), 2),
            "livraisons": round(compute_variation(livraisons_sorted), 2),
            "produits_livres": round(compute_variation(produits_sorted), 2),
        },
        "series": {
            "connexions": connexions_sorted,
            "livraisons": livraisons_sorted,
            "produits_livres": produits_sorted,
        },
        "totaux": {
            "connexions": sum(c["count"] for c in connexions_sorted),
            "livraisons": sum(l["count"] for l in livraisons_sorted),
            "produits_livres": sum(p["count"] for p in produits_sorted),
            "utilisateurs_actifs": utilisateurs_actifs,
            "magasins_actifs": magasins_actifs
        }
    }


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
            magasin = MagasinModel.get_magasin_by_id(magasin_id)
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



# Meilleurs magasins par nombre de livraisons

def get_top_magasin_par_chiffre_affaire(limit=5):
    """
    Retourne les N meilleurs magasins triés par chiffre d'affaires total (livraisons).
    """
    livraisons = LivraisonModel.get_all_livraisons_plateforme()
    revenus_par_magasin = defaultdict(float)

    for l in livraisons:
        magasin_id = l.get("magasin_id")
        montant = l.get("montant_total", 0)
        if magasin_id:
            revenus_par_magasin[str(magasin_id)] += montant

    # Trier par montant décroissant
    sorted_items = sorted(revenus_par_magasin.items(), key=lambda x: x[1], reverse=True)
    top_magasins = []

    for magasin_id, total in sorted_items[:limit]:
        magasin = MagasinModel.get_magasin_by_id(magasin_id)
        if magasin:
            top_magasins.append({
                "magasin_id": magasin_id,
                "denomination": magasin.get("denomination", "Inconnu"),
                "chiffre_affaire": round(total, 2)
            })

    return {
        "meilleurs_magasins": top_magasins,
        "granularite": "totale"
    }



# premier compartiment pour les statistiques de staff
def get_nombre_magasins_total():
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    start_date = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
    end_date = today
    periode_duree = end_date - start_date

    previous_start = start_date - periode_duree
    previous_end = start_date

    # Magasins créés cette semaine et la précédente
    current = list(MagasinModel.collection.find({"created_at": {"$gte": start_date, "$lt": end_date}}))
    previous = list(MagasinModel.collection.find({"created_at": {"$gte": previous_start, "$lt": previous_end}}))

    total = MagasinModel.collection.count_documents({})

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
def get_nombre_admins_managers_total():
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



# nombre de livreurs total
def get_nombre_livreurs_total():
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    start_date = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
    end_date = today
    periode_duree = end_date - start_date

    previous_start = start_date - periode_duree
    previous_end = start_date

    current = list(UserModel.collection.find({
        "role": "livreur",
        "created_at": {"$gte": start_date, "$lt": end_date}
    }))
    previous = list(UserModel.collection.find({
        "role": "livreur",
        "created_at": {"$gte": previous_start, "$lt": previous_end}
    }))

    total = UserModel.collection.count_documents({"role": "livreur"})

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

# nombre total de clients
def get_nombre_clients_total():
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    start_date = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
    end_date = today
    periode_duree = end_date - start_date

    previous_start = start_date - periode_duree
    previous_end = start_date

    current = list(ClientModel.collection.find({
    
        "created_at": {"$gte": start_date, "$lt": end_date}
    }))
    previous = list(ClientModel.collection.find({

        "created_at": {"$gte": previous_start, "$lt": previous_end}
    }))

    # Compter le nombre total de clients
    total = ClientModel.collection.count_documents({})
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

    


def get_suggestions_service(nom=None, categorie=None, description=None, tags=None):
    images = ImageStaffModel.get_image_by_critere(nom, categorie, description, tags)
    
    # Retourner les images selon les dates de création les plus récentes    
    images.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True) 
    
    return [{
        "_id": str(img["_id"]),
        "filename": f"{request.host_url}uploads/staff_images/{img['filename']}",
        "nom": img["nom"],
        "description": img.get("description", ""),
        "categorie": img.get("categorie", ""),
        "tags": img.get("tags", [])
    } for img in images]
