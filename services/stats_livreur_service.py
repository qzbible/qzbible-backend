from models.client_model import ClientModel 
from models.livraison_model import LivraisonModel
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from collections import defaultdict
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


def get_villes_livraison_livreur(livreur_id):
    """
    Retourne les zones (quartiers) de vente des 4 meilleures villes pour un livreur.
    Pour chaque ville : les quartiers avec montant total, quantité, nombre livraisons et pourcentages.
    """

    livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)

    # Structure : villes → quartiers → stats
    villes_stats = defaultdict(lambda: defaultdict(lambda: {
        "quartier": "",
        "nombre_livraisons": 0,
        "quantite_totale": 0,
        "montant_total": 0
    }))

    villes_totaux = defaultdict(float)  # montant total par ville

    for livraison in livraisons:
        client = ClientModel.get_client_by_id(str(livraison["client_id"]))
        if not client:
            continue

        ville = client.get("ville", "Inconnue")
        quartier = client.get("quartier", "Inconnu")

        montant = livraison.get("montant_total", 0)
        quantite = livraison.get("quantite", 0)

        stats = villes_stats[ville][quartier]
        stats["quartier"] = quartier
        stats["nombre_livraisons"] += 1
        stats["quantite_totale"] += quantite
        stats["montant_total"] += montant

        villes_totaux[ville] += montant

    # Sélection des 4 meilleures villes en fonction du montant
    top_villes = sorted(villes_totaux.items(), key=lambda x: x[1], reverse=True)[:4]

    resultat = []

    for ville, montant_total_ville in top_villes:
        quartiers = list(villes_stats[ville].values())
        total_livraisons = sum(q["nombre_livraisons"] for q in quartiers)
        total_quantite = sum(q["quantite_totale"] for q in quartiers)

        for q in quartiers:
            q["pourcentage_livraisons"] = round((q["nombre_livraisons"] / total_livraisons) * 100, 2) if total_livraisons else 0
            q["pourcentage_quantite"] = round((q["quantite_totale"] / total_quantite) * 100, 2) if total_quantite else 0
            q["pourcentage_montant"] = round((q["montant_total"] / montant_total_ville) * 100, 2) if montant_total_ville else 0

        resultat.append({
            "ville": ville,
            "montant_total_ville": round(montant_total_ville, 2),
            "quartiers": sorted(quartiers, key=lambda x: x["montant_total"], reverse=True)
        })

    return resultat




"""
    Calcule le chiffre d’affaires total et l'évolution sur une periode.
    Le compare à la même période précédente.
    Retourne la valeur actuelle et la variation en pourcentage.
"""


def get_chiffre_affaires_total_par_livreur(livreur_id):
    """
    Retourne :
    - Le chiffre d'affaires total du livreur (toutes périodes),
    - La variation du chiffre d'affaires de cette semaine par rapport à la précédente.
    """
    today = datetime.now()

    # Semaine actuelle
    start_of_week = today - timedelta(days=today.weekday())  # Lundi
    start_date = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
    end_date = today # exemple :  jeudi 9 mai 2025
    periode_duree = end_date - start_date # => 9 mai - 5 mai = 4 jours

    # Semaine précédente
    previous_start = start_date - periode_duree # exemple : # => 5 mai - 4 jours = 1er mai 2025
    previous_end = start_date # => 5 mai 2025

    # Chiffre d'affaires de la semaine actuelle
    current_livraisons = LivraisonModel.get_livraisons_between_dates(start_date, end_date, livreur_id)
    current_total = sum(l.get("montant_total", 0) for l in current_livraisons)

    # Chiffre d'affaires de la semaine précédente
    previous_livraisons = LivraisonModel.get_livraisons_between_dates(previous_start, previous_end, livreur_id)
    previous_total = sum(l.get("montant_total", 0) for l in previous_livraisons)

    # Calcul de la variation
    if previous_total == 0:
        variation = 100.0 if current_total > 0 else 0.0
    else:
        variation = ((current_total - previous_total) / previous_total) * 100

    # Chiffre d'affaires global (toutes périodes)
    all_livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)
    total = sum(l.get("montant_total", 0) for l in all_livraisons)

    return {
        "valeur": round(total, 2),  # Chiffre d'affaires total toutes périodes
        "variation_percent": round(variation, 2),
        "periode": {
            "debut": start_date.isoformat(),
            "fin": end_date.isoformat()
        }
    }




def get_week_date_range(year, week):
    """Retourne le lundi et le dimanche de la semaine ISO donnée."""
    first_day = date.fromisocalendar(year, week, 1)
    last_day = first_day + timedelta(days=6)
    return first_day, last_day


def get_revenus_par_periode_par_livreur(livreur_id, granularity='jour', page=0):
    """
    Retourne le revenu total cumulé d’un livreur pour un bloc de périodes donné
    (4 unités temporelles ou 7 jours) selon la granularité et la page demandée.
    """
    livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)
    revenus_par_periode = defaultdict(float)

    # Agrégation des revenus par période
    for l in livraisons:
        date_obj = l.get("created_at")
        if not date_obj:
            continue
        montant = l.get("montant_total", 0)

        if granularity == "jour":
            key = date_obj.strftime("%Y-%m-%d")
        elif granularity == "semaine":
            iso_year, iso_week, _ = date_obj.isocalendar()
            key = f"{iso_year}-W{iso_week:02d}"
        elif granularity == "mois":
            key = f"{date_obj.year}-{date_obj.month:02d}"
        elif granularity == "annee":
            key = str(date_obj.year)
        else:
            raise ValueError("Granularité invalide : 'jour', 'semaine', 'mois', 'annee' attendue")

        revenus_par_periode[key] += montant

    # Construction des périodes cibles selon granularité et page
    now = date.today()
    periodes = []

    if granularity == "jour":
        # On récupère la semaine courante et on décale
        current_monday = now - timedelta(days=now.weekday())
        start = current_monday + timedelta(weeks=page)
        for i in range(7):
            day = start + timedelta(days=i)
            key = day.strftime("%Y-%m-%d")
            periodes.append((key, day, day))
    
    elif granularity == "semaine":
        current_year, current_week, _ = now.isocalendar()
        start_week = current_week + (page * 4)
        start_year = current_year
        for i in range(4):
            week = start_week + i
            year = start_year
            # Gestion du débordement d'année
            while week > 52:
                week -= 52
                year += 1
            while week < 1:
                week += 52
                year -= 1
            start, end = get_week_date_range(year, week)
            key = f"{year}-W{week:02d}"
            periodes.append((key, start, end))

    elif granularity == "mois":
        base = now.replace(day=1) + relativedelta(months=page * 4)
        for i in range(4):
            d = base + relativedelta(months=i)
            key = f"{d.year}-{d.month:02d}"
            start = d
            end = (d + relativedelta(months=1)) - timedelta(days=1)
            periodes.append((key, start, end))

    elif granularity == "annee":
        start_year = now.year + (page * 4)
        for i in range(4):
            y = start_year + i
            key = str(y)
            start = date(y, 1, 1)
            end = date(y, 12, 31)
            periodes.append((key, start, end))

    # Construction des résultats
    detail = []
    revenu_total = 0.0
    for key, start, end in periodes:
        montant = revenus_par_periode.get(key, 0.0)
        revenu_total += montant
        entry = {
            "periode": key,
            "montant_total": round(montant, 2),
            "debut": str(start),
            "fin": str(end)
        }
        if montant == 0 and end > now:
            entry["incomplet"] = True
        detail.append(entry)

    # Variation (sur les 2 dernières périodes de la page courante uniquement)
    variation = 0.0
    if len(detail) >= 2:
        montant_precedent = detail[-2]["montant_total"]
        montant_courant = detail[-1]["montant_total"]
        if montant_precedent == 0:
            variation = 100.0 if montant_courant > 0 else 0.0
        else:
            variation = ((montant_courant - montant_precedent) / montant_precedent) * 100

    return {
        "valeur": round(revenu_total, 2),
        "variation_percent": round(variation, 2),
        "granularite": granularity,
        "page": page,
        "detail": detail
    }


# Statistiques de paiement par livreur

def get_statistiques_paiement_par_livreur(livreur_id):
    """
    Retourne la répartition des paiements faits par un livreur,
    sous forme de pourcentages.
    """
    livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)
    repartition = defaultdict(int)

    for l in livraisons:
        statut = l.get("statut_paiement", "inconnu").lower()
        repartition[statut] += 1

    total = sum(repartition.values())
    if total == 0:
        return []

    return [
        {
            "mode_paiement": k,
            "pourcentage": round((v / total) * 100, 2),
            "nombre": v
        }
        for k, v in repartition.items()
    ]



# Nombre de livraison total par livreur
def get_nombre_livraisons_total_par_livreur(livreur_id):
    """
    Retourne :
    - Le nombre total de livraisons effectuées (toutes périodes),
    - La variation par rapport à la semaine précédente.
    """
    today = datetime.now()

    # Semaine actuelle
    # today.weekday() = 0  retourne le jour de la semaine (0 pour lundi à 6 pour dimanche).
    start_of_week = today - timedelta(days=today.weekday())  # donne le lundi de la semaine actuelle.
    start_date = datetime(start_of_week.year, start_of_week.month, start_of_week.day) # Formalise ce lundi à minuit.
    end_date = today # est maintenant (l'instant courant).
    periode_duree = end_date - start_date # est la durée de la période actuelle (typiquement du lundi jusqu’à maintenant).

    # Semaine précédente
    previous_start = start_date - periode_duree
    previous_end = start_date

    # Livraisons de la semaine actuelle et précédente
    current_livraisons = LivraisonModel.get_livraisons_between_dates(start_date, end_date, livreur_id=livreur_id)
    previous_livraisons = LivraisonModel.get_livraisons_between_dates(previous_start, previous_end, livreur_id=livreur_id)

    current_total = len(current_livraisons)
    previous_total = len(previous_livraisons)

    if previous_total == 0:
        variation = 100.0 if current_total > 0 else 0.0
    else:
        variation = ((current_total - previous_total) / previous_total) * 100

    # Total global (toutes périodes)
    all_livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)
    total = len(all_livraisons)

    return {
        "valeur": total,  # Livraisons totales
        "variation_percent": round(variation, 2),
        "periode": {
            "debut": start_date.isoformat(),
            "fin": end_date.isoformat()
        }
    }


def get_nombre_clients_uniques_par_livreur(livreur_id):
    """
    Retourne :
    - Le nombre total de clients uniques servis (toutes périodes),
    - Le nombre total de livraisons effectuées,
    - La variation du nombre de clients uniques cette semaine par rapport à la précédente.
    """
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    start_date = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
    end_date = today
    periode_duree = end_date - start_date
    previous_start = start_date - periode_duree
    previous_end = start_date

    # Livraisons sur la semaine actuelle et précédente
    current_livraisons = LivraisonModel.get_livraisons_between_dates(start_date, end_date, livreur_id)
    previous_livraisons = LivraisonModel.get_livraisons_between_dates(previous_start, previous_end, livreur_id)

    current_clients = {str(l["client_id"]) for l in current_livraisons}
    previous_clients = {str(l["client_id"]) for l in previous_livraisons}

    current_count = len(current_clients)
    previous_count = len(previous_clients)

    if previous_count == 0:
        variation = 100.0 if current_count > 0 else 0.0
    else:
        variation = ((current_count - previous_count) / previous_count) * 100

    # Clients uniques et livraisons totales sur toutes les périodes
    all_livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)
    all_clients = {str(l["client_id"]) for l in all_livraisons}
    total_livraisons = len(all_livraisons)

    return {
        "valeur": len(all_clients),  # clients uniques (historique)
        "nombre_livraisons_total": total_livraisons,
        "variation_percent": round(variation, 2),
        "periode": {
            "debut": start_date.isoformat(),
            "fin": end_date.isoformat()
        }
    }


def get_nombre_produits_uniques_par_livreur(livreur_id):
    """
    Retourne :
    - Le nombre total de produits uniques livrés par un livreur (historique complet),
    - La quantité totale de produits livrés (historique),
    - Et la variation sur les produits uniques par rapport à la semaine précédente.
    """
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    start_date = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
    end_date = today
    periode_duree = end_date - start_date
    previous_start = start_date - periode_duree
    previous_end = start_date

    # Toutes les livraisons du livreur (historique complet)
    all_livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)

    # Calcul des produits uniques et quantité totale (historique)
    produits_uniques = set()
    quantite_totale = 0

    for l in all_livraisons:
        for p in l.get("produits", []):
            produits_uniques.add(str(p["produit_id"]))
            quantite_totale += p.get("quantite", 0)

    # Livraisons de la semaine actuelle
    current_livraisons = LivraisonModel.get_livraisons_between_dates(start_date, end_date, livreur_id)
    current_produits = set()
    for l in current_livraisons:
        current_produits.update(str(p["produit_id"]) for p in l.get("produits", []))

    # Livraisons de la semaine précédente
    previous_livraisons = LivraisonModel.get_livraisons_between_dates(previous_start, previous_end, livreur_id)
    previous_produits = set()
    for l in previous_livraisons:
        previous_produits.update(str(p["produit_id"]) for p in l.get("produits", []))

    current_count = len(current_produits)
    previous_count = len(previous_produits)

    if previous_count == 0:
        variation = 100.0 if current_count > 0 else 0.0
    else:
        variation = ((current_count - previous_count) / previous_count) * 100

    return {
        "valeur": len(produits_uniques),
        "quantite_totale": quantite_totale,
        "variation_percent": round(variation, 2),
        "periode": {
            "debut": start_date.isoformat(),
            "fin": end_date.isoformat()
        }
    }
