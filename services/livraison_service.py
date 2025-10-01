# services/livraison_services.py
from bson import ObjectId
from datetime import datetime
from models.livraison_model import LivraisonModel
from models.stock_livreur_model import StockLivreurModel
from schemas.livraison_schema import LivraisonSchema, LivraisonManagerSchema, RetourLivraisonSchema
from marshmallow import ValidationError
from models.produit_model import ProduitModel
from models.client_model import ClientModel
from models.retour_model import RetourLivraisonModel
from models.user_model import UserModel

"""
    Cette fonction gère la création d'une livraison. Elle valide les données d'entrée à l'aide du schéma, 
    vérifie si le livreur a suffisamment de stock, crée la livraison dans la base de données, puis met à 
    jour le stock du livreur.
"""


#########################################################
# Nouvelle version prenant en charge le conditionnement #
#########################################################
def creer_livraison(data):
    """
    Crée une nouvelle livraison en vérifiant si le livreur a assez de stock.
    """
    try:
        schema = LivraisonSchema()
        validated_data = schema.load(data)
    except ValidationError as err:
        return {"error": err.messages}, 400

    livreur_id = validated_data["livreur_id"]
    produits_input = validated_data["produits"]
    produits_final = []

    for produit in produits_input:
        produit_id = produit["produit_id"]
        produit_data = ProduitModel.get_by_id(produit_id)
        if not produit_data:
            return {"error": f"Produit {produit_id} introuvable"}, 404

        # Gestion avec ou sans conditionnement
        if "conditionnement_id" in produit and "quantite_conditionnement" in produit:
            conditionnement = ProduitModel.get_conditionnement_by_id(produit_id, produit["conditionnement_id"])
            if not conditionnement:
                return {"error": f"Conditionnement introuvable pour le produit {produit_id}"}, 404

            produits_final.append({
                "produit_id": ObjectId(produit_id),
                "nom": produit_data["nom"],
                "quantite": int(produit["quantite_conditionnement"]) * int(conditionnement["facteur"]),
                "prix": float(conditionnement["prix_conditionnement"])/ int(conditionnement["facteur"]),
                "conditionnement_id": produit["conditionnement_id"],
                "facteur": int(conditionnement["facteur"]),
                "is_conditionne": True
            })
        else:
            produits_final.append({
                "produit_id": ObjectId(produit_id),
                "nom": produit_data["nom"],
                "quantite": int(produit["quantite"]),
                "prix": float(produit_data["prix"]),
                "is_conditionne": False
            })

    # Vérifier le stock
    ok, error = verifier_stock_livreur(livreur_id, produits_final)
    if not ok:
        return {"error": error}, 400

    # Créer la livraison
    livraison_id = LivraisonModel.create_livraison(validated_data, produits_final)

    # Mise à jour du stock
    StockLivreurModel.retirer_stock(livreur_id, produits_final)

    return {"livraison_id": livraison_id}, 201


# Vérifie si le livreur a assez de stock pour chaque produit demandé
def verifier_stock_livreur(livreur_id, produits_demandes):
    """
    Vérifie si le livreur a assez de stock pour chaque produit demandé.
    Retourne (True, None) si tout est bon, sinon (False, message d'erreur).
    """
    stock_dispo = StockLivreurModel.get_stock_livreur(livreur_id)

    # Conversion explicite en string
    stock_map = {
        str(item["produit_id"]): int(item["quantite"])
        for item in stock_dispo if "produit_id" in item and "quantite" in item
    }

    #print("Stock_map:", stock_map)
    #print("Produits demandés:", produits_demandes)

    for produit in produits_demandes:
        pid = str(produit["produit_id"])
        qte = int(produit["quantite"])

        if pid not in stock_map:
            return False, f"Produit {pid} non disponible pour ce livreur."
        if stock_map[pid] < qte:
            return False, f"Quantité insuffisante pour le produit {pid}."

    return True, None


# Vérifie si magasin a assez de stock pour chaque produit demandé
def verifier_stock_magasin(magasin_id, produits_demandes):
    """
    Vérifie si le magasin a assez de stock pour chaque produit demandé.
    Retourne (True, None) si tout est bon, sinon (False, message d'erreur).
    """
     # Validation des données
  
    stock_dispo = ProduitModel.get_all_by_magasin(magasin_id)
    stock_map = {str(item["_id"]): item["quantite"] for item in stock_dispo}
    
    for produit in produits_demandes:
        pid = produit['produit_id']
        qte = int(produit["quantite"])
        
        if pid not in stock_map:
            return False, f"Produit {pid} non disponible dans ce magasin."
        if stock_map[pid] <qte:
            return False, f"Quantité insuffisante pour le produit {pid}"

    return True, None



# Nouvelle version de création d'une livraison par un manager
def creer_livraison_by_manager(data):
    """
    Crée une livraison par un manager/admin depuis un magasin.
    """
    try:
        schema = LivraisonManagerSchema()
        validated_data = schema.load(data)
    except ValidationError as err:
        return {"error": err.messages}, 400

    manager_id = validated_data["manager_id"]
    validated_data["manager_id"] = manager_id
    validated_data["livreur_id"] = manager_id
    produits_input = validated_data["produits"]
    produits_final = []

    for produit in produits_input:
        produit_id = produit["produit_id"]
        produit_data = ProduitModel.get_by_id(produit_id)
        if not produit_data:
            return {"error": f"Produit {produit_id} introuvable"}, 404

        if "conditionnement_id" in produit and "quantite_conditionnement" in produit:
            conditionnement = ProduitModel.get_conditionnement_by_id(produit_id, produit["conditionnement_id"])
            if not conditionnement:
                return {"error": f"Conditionnement introuvable pour le produit {produit_id}"}, 404

            produits_final.append({
                "produit_id": produit_id,
                "nom": produit_data["nom"],
                "quantite": int(produit["quantite_conditionnement"]) * int(conditionnement["facteur"]),
                "prix": float(conditionnement["prix_conditionnement"])/ int(conditionnement["facteur"]),
                "conditionnement_id": produit["conditionnement_id"],
                "facteur": int(conditionnement["facteur"]),
                "is_conditionne": True,
                "type_vente" : "conditionne" # unitaire
            })
        else:
            produits_final.append({
                "produit_id": produit_id,
                "nom": produit_data["nom"],
                "quantite": int(produit["quantite"]),
                "prix": float(produit_data["prix"]),
                "is_conditionne": False
            })

    ok, error = verifier_stock_magasin(data["magasin_id"], produits_final)
    if not ok:
        return {"error": error}, 400

    livraison_id = LivraisonModel.create_livraison(validated_data, produits_final)

    for produit in produits_final:
        ProduitModel.decrement_stock(
            produit_id=produit["produit_id"],
            quantite=produit["quantite"],
            acteur={"user_id": manager_id},
            type_mouvement="livraison manager"
        )

    return {"message": "Livraison créée avec succès", "livraison_id": livraison_id}, 201



def serialize_livraison(livraison):
    # Récupération des informations du client
    client_data = ClientModel.get_client_by_id(livraison["client_id"])
    if client_data:
        client_data.pop("_id", None)  # Supprimer l'ID
    # Récupérer le nom du livreur
    
    livreur_data = UserModel.get_user_by_id(livraison["livreur_id"])
    if livreur_data:
        livreur_data.pop("_id", None)  # Supprimer l'ID
    # extraire juste le nom du livreur
    nom_livreur = livreur_data.get("name", "") + " " + livreur_data.get("first_name", "") if livreur_data else ""

    # Arrondir les montants à 2 chiffres après la virgule
    def round_float(val):
        try:
            return round(float(val), 2)
        except (TypeError, ValueError):
            return 0.0

    montant_total = round_float(livraison.get("montant_total", 0))
    montant_paye = round_float(livraison.get("montant_paye", 0))
    retour = round_float(livraison.get("retour", 0))
    ristourne = round_float(livraison.get("ristourne", 0))

    montant_restant = round_float(montant_total - montant_paye) if montant_paye < montant_total else 0.0

    # Sérialisation de la livraison
    livraison_serialized = {
        "id": str(livraison["_id"]),
        "livreur_id": str(livraison["livreur_id"]),
        "nom_livreur": nom_livreur,
        "magasin_id": str(livraison["magasin_id"]),
        "client_id": str(livraison["client_id"]),
        "client": client_data,
        "produits": livraison["produits"],
        "montant_total": montant_total,
        "montant_paye": montant_paye,
        "montant_restant": montant_restant,
        "quantite": livraison["quantite"],
        "statut_paiement": livraison["statut_paiement"],
        "statut_livraison": livraison["statut_livraison"],
        "retour": retour,
        "ristourne": ristourne,
        "have_ristourne": livraison.get("have_ristourne", False),
        "have_retour": livraison.get("have_retour", False),
        "date_commande": livraison["date_commande"].isoformat() if isinstance(livraison["date_commande"], datetime) else str(livraison["date_commande"]),
        "created_at": livraison["created_at"].isoformat() if isinstance(livraison["created_at"], datetime) else str(livraison["created_at"]),
        "updated_at": livraison["updated_at"].isoformat() if isinstance(livraison["updated_at"], datetime) else str(livraison["updated_at"]),
    }

    # Ajout des retours si have_ristourne est True
    if livraison.get("have_retour") is True:
        retours = RetourLivraisonModel.get_retours_by_livraison(livraison["_id"])
        livraison_serialized["retours"] = [
            {
                "id": str(r["_id"]),
                "produits": r.get("produits", []),
                "motif": r.get("motif", ""),
                "manager_id": str(r["manager_id"]) if r.get("manager_id") else None,
                "livreur_id": str(r["livreur_id"]) if r.get("livreur_id") else None,
                "created_at": r.get("created_at")
            } for r in retours
        ]
    else:
        livraison_serialized["retours"] = []

    return livraison_serialized


# Retourne toutes les livraison d'un livreur 
def get_livraison_livreur(livreur_id):
    """
    Récupérer les livraisons d'un livreur
    """
    livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)
    # Trie les livraisons par date de création (plus récente en premier)
      
    livraisons = sorted(
        livraisons,
        key=lambda l: l.get("created_at", datetime.min),
        reverse=True
    )
    livraisons_nettoyees = [serialize_livraison(l) for l in livraisons]
    return livraisons_nettoyees, 200


#get_livraison_managers
def get_livraison_managers():
    """
    Retourne toutes les livraisons d'un magasin.
    """
    livraisons = LivraisonModel.get_all_livraisons()
    
    # chaque livraison enrichir avec les informations des conditionnements si présents
    for livraison in livraisons:
        produits_enrichis = []
        for item in livraison["produits"]:
            produit_id = item.get("produit_id")
            produit_info = ProduitModel.get_by_id(produit_id)

            conditionnement_nom = None
            if item.get("is_conditionne", False) and item.get("conditionnement_id"):
                conditionnement = ProduitModel.get_conditionnement_by_id(
                    produit_id,
                    item["conditionnement_id"]
                )
                if conditionnement:
                    conditionnement_nom = conditionnement.get("nom")

            enriched_item = {
                "produit_id": str(produit_id),
                "quantite": item.get("quantite"),
                "prix": item.get("prix"),
                "nom": produit_info.get("nom") if produit_info else item.get("nom"),
                "categorie": produit_info.get("categorie") if produit_info else None,
                "unite": produit_info.get("unite") if produit_info else None,
                "image": produit_info.get("image") if produit_info else None,

                # Champs pour retours conditionnés
                "is_conditionne": item.get("is_conditionne", False),
                "conditionnement_id": item.get("conditionnement_id"),
                "conditionnement_nom": conditionnement_nom,  # ajout ici
                "facteur": item.get("facteur"),
            }

            produits_enrichis.append(enriched_item)

        livraison["produits"] = produits_enrichis
    
    # Trie les livraisons par date de création (plus récente en premier)
    livraisons = sorted(
        livraisons,
        key=lambda l: l.get("created_at", datetime.min),
        reverse=True
    )
    
    livraisons_nettoyees = [serialize_livraison(l) for l in livraisons]
    return livraisons_nettoyees, 200



# Retourne les 5 dernières livraisons d'un livreur
def get_livraisons_recentes_par_livreur(livreur_id, limit=5):
    """
    Retourne les N livraisons les plus récentes d’un livreur.
    """
    # Récupère toutes les livraisons du livreur
    livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)

    # Trie les livraisons par date de création (plus récente en premier)
    livraisons_triees = sorted(
        livraisons,
        key=lambda l: l.get("created_at", datetime.min),
        reverse=True
    )

    # Prend uniquement les 'limit' premières
    livraisons_recentes = livraisons_triees[:limit]

    # Sérialise les livraisons
    return [serialize_livraison(l) for l in livraisons_recentes], 200


# Avoir les détails completes d'une livraison pour un livreur
def details_livraison_service(livreur_id, livraison_id):
    """
    Retourne les détails enrichis d'une livraison pour un livreur donné,
    incluant les noms de conditionnements si présents.
    """
    # 1. Récupération de la livraison
    livraison = LivraisonModel.get_livraison_by_id(livraison_id)
    if not livraison:
        return {"error": "Livraison introuvable"}, 404

    # 2. Vérification de propriété (optionnelle)
    # if str(livraison["livreur_id"]) != str(livreur_id):
    #     return {"error": "Accès non autorisé à cette livraison"}, 403

    # 3. Enrichir chaque produit
    produits_enrichis = []
    for item in livraison["produits"]:
        produit_id = item.get("produit_id")
        produit_info = ProduitModel.get_by_id(produit_id)

        conditionnement_nom = None
        if item.get("is_conditionne", False) and item.get("conditionnement_id"):
            conditionnement = ProduitModel.get_conditionnement_by_id(
                produit_id,
                item["conditionnement_id"]
            )
            if conditionnement:
                conditionnement_nom = conditionnement.get("nom")

        enriched_item = {
            "produit_id": str(produit_id),
            "quantite": item.get("quantite"),
            "prix": item.get("prix"),
            "nom": produit_info.get("nom") if produit_info else item.get("nom"),
            "categorie": produit_info.get("categorie") if produit_info else None,
            "unite": produit_info.get("unite") if produit_info else None,
            "image": produit_info.get("image") if produit_info else None,

            # Champs pour retours conditionnés
            "is_conditionne": item.get("is_conditionne", False),
            "conditionnement_id": item.get("conditionnement_id"),
            "conditionnement_nom": conditionnement_nom,  # ajout ici
            "facteur": item.get("facteur"),
        }

        produits_enrichis.append(enriched_item)

    # 4. Sérialiser la livraison
    livraison_detail = serialize_livraison(livraison)

    # 5. Injecter les produits enrichis
    livraison_detail["produits"] = produits_enrichis

    return livraison_detail, 200





def ajouter_paiement_service(livreur_id, livraison_id, montant):
    """
    Ajout un paiement à une livraison en vérifiant que le livreur est bien propriétaire de la livraison
    """
    
    # Vérification que la livraison appartient bien à ce livreur
    livraison = LivraisonModel.collection.find_one({
        "_id": ObjectId(livraison_id),
        "livreur_id":ObjectId(livreur_id)
    })
    
    if not livraison:
        return {"message" : "Livraison introuvable ou accès non autorisé"}, 404
    
    # Appel de la méthode statique pour ajouter le paiement
    result = LivraisonModel.ajouter_paiement(livraison_id, montant)
    
    if not result:
        return {"message" : "Erreur lors de l'ajout du paiement"}, 500
    return {"message" : "Paiement ajouté avec succès"}, 200


def get_livraisons_filtrees_par_livreur(livreur_id, filters=None):
    """-1356886
    Récupère les livraisons d’un livreur avec des filtres dynamiques :
    - colonnes simples : status, client_id, etc.
    - date: exacte (via `date`) ou plage (`date_min`, `date_max`)
    - montant_total: plage (`montant_min`, `montant_max`)
    """
    livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)
    
    def match_filters(livraison):
        created_at = livraison.get("created_at")
        montant_total = livraison.get("montant_total", 0)

        for key, value in filters.items():
            if key == "date":
                if not created_at or created_at.strftime("%Y-%m-%d") != value:
                    return False
            elif key == "date_min":
                if not created_at or created_at < datetime.strptime(value, "%Y-%m-%d"):
                    return False
            elif key == "date_max":
                if not created_at or created_at > datetime.strptime(value, "%Y-%m-%d"):
                    return False
            elif key == "montant_min":
                if montant_total < float(value):
                    return False
            elif key == "montant_max":
                if montant_total > float(value):
                    return False
            else:
                # Comparaison directe pour d’autres attributs
                if str(livraison.get(key)) != str(value):
                    return False
        return True
    
    if filters:
        livraisons = [l for l in livraisons if match_filters(l)]

    livraisons = sorted(
        livraisons,
        key=lambda l: l.get("created_at", datetime.min),
        reverse=True
    )

    livraisons_nettoyees = [serialize_livraison(l) for l in livraisons]
    return livraisons_nettoyees, 200



  
# Retourne les 5 dernières livraisons d'un magasin
def get_livraisons_recentes_total(limit=5):
    """
    Retourne les N livraisons les plus récentes d’un livreur.
    """
    # Récupère toutes les livraisons du livreur
    livraisons = LivraisonModel.get_all_livraisons()

    # Trie les livraisons par date de création (plus récente en premier)
    livraisons_triees = sorted(
        livraisons,
        key=lambda l: l.get("created_at", datetime.min),
        reverse=True
    )

    # Prend uniquement les 'limit' premières
    livraisons_recentes = livraisons_triees[:limit]

    # Sérialise les livraisons
    return [serialize_livraison(l) for l in livraisons_recentes], 200






# Livraison livreur avec filtres dynamiques
def get_livraison_livreurs(livreur_id, filters=None):
    livraisons = LivraisonModel.get_livraisons_by_livreur(livreur_id)
    livraisons = sorted(livraisons, key=lambda l: l.get("created_at", datetime.min), reverse=True)

    livraisons_nettoyees = [serialize_livraison(l) for l in livraisons]

    if filters:
        def match(l):
            if filters["statut_paiement"] and l["statut_paiement"] != filters["statut_paiement"]:
                return False
            if filters["statut_livraison"] and l["statut_livraison"] != filters["statut_livraison"]:
                return False
            if filters["date_commande"]:
                try:
                    date_str = l["date_commande"].split("T")[0]
                    if date_str != filters["date_commande"]:
                        return False
                except Exception:
                    return False
            if filters["client_nom"]:
                client_nom = (l["client"] or {}).get("nom", "").lower()
                if filters["client_nom"].lower() not in client_nom:
                    return False
            return True

        livraisons_nettoyees = list(filter(match, livraisons_nettoyees))

    return livraisons_nettoyees, 200


# Supprimer une livraison et entrainer la réintégration des produits dans le stock du livreur
def supprimer_livraison_service(livraison_id):
    """
    Supprimer une livraison et réintégrer les produits dans le stock du livreur.
    """
    # Vérifier si la livraison existe et appartient au livreur
    livraison = LivraisonModel.get_livraison_by_id(livraison_id)
    
    if not livraison:
        return {"error": "Livraison introuvable"}, 404

    
    # Réintégrer les produits dans le stock du livreur
    StockLivreurModel.ajouter_stock(livraison["livreur_id"], livraison["produits"])
    
    # Supprimer la livraison
    LivraisonModel.collection.delete_one({"_id": ObjectId(livraison_id)})
    
    return {"message": "Livraison supprimée avec succès"}, 200    


def ajouter_paiement_service(livraison_id, montant):
    """
    Service de mise à jour du montant payé pour une livraison.
    : param livraison_id: ID de la livraison
    : param montant : à ajouter au paiement
    """
    
    if not ObjectId.is_valid(livraison_id):
        return {"error" : "ID de livraison invalide"}, 400
    
    if not isinstance(montant, (int, float)) or montant <= 0:
        return {"error" : "Le montant doit être un nombre positif"}, 400
    
    resultat = LivraisonModel.ajouter_paiement(livraison_id, montant)
    if not resultat:
        return {"error" : "Livraison non trouvée"}, 404
    
    if "message" in resultat:
        return {"message" : resultat["message"]}, 400
    
    # Nettoyage pour retour
    resultat['_id'] = str(resultat['_id'])
    resultat["livreur_id"] = str(resultat["livreur_id"])
    resultat["client_id"] = str(resultat["client_id"])
    resultat["magasin_id"] = str(resultat["magasin_id"])
    resultat["created_at"] = resultat["created_at"].isoformat()
    resultat["updated_at"] = resultat["updated_at"].isoformat()

    return {"message": "Paiement mis à jour avec succès", "livraison": resultat}, 200





# Service pour gérer le retour d'une livraison
"""

def creer_retour_livraison(data):
   
    try:
        schema = RetourLivraisonSchema()
        validated_data = schema.load(data)
    except ValidationError as err:
        return 
    {"error": err.messages}, 400

    livraison_id = validated_data["livraison_id"]
    produits = validated_data["produits"]

    livraison = LivraisonModel.get_livraison_by_id(livraison_id)
    if not livraison:
        return {"error": "Livraison introuvable"}, 404

    produits_livres = livraison.get("produits", [])

    # Indexation des produits livrés
    produits_livres_dict = {}
    for p in produits_livres:
        key = (
            str(p["produit_id"]),
            str(p.get("conditionnement_id")) if p.get("is_conditionne") else "none"
        )
        produits_livres_dict[key] = p

    montant_ristourne_retour = 0
    total_retournes = {}

    for produit in produits:
        key = (
            str(produit["produit_id"]),
            str(produit.get("conditionnement_id")) if produit.get("is_conditionne") else "none"
        )
        quantite_retour = produit["quantite"]
        produit_livre = produits_livres_dict.get(key)

        if not produit_livre:
            return {"error": f"Produit non trouvé dans la livraison (clé: {key})"}, 400

        quantite_livree = produit_livre["quantite"]
        deja_retournee = total_retournes.get(key, 0)

        if quantite_retour + deja_retournee > quantite_livree:
            return {"error": f"Retour impossible : la quantité ({quantite_retour}) dépasse la quantité livrée ({quantite_livree}) pour le produit {produit['produit_id']}"}, 400

        total_retournes[key] = deja_retournee + quantite_retour
        montant_ristourne_retour += produit_livre["prix"] * quantite_retour

    # Enregistrement du retour
    retour_id = RetourLivraisonModel.enregistrer_retour(validated_data)

    # Réintégration du stock
    if livraison.get("livreur_id") and not livraison.get("manager_id"):
        StockLivreurModel.ajouter_stock(validated_data["livreur_id"], produits)
        for produit in produits:
            ProduitModel.ajouter_mouvement_stock(produit["produit_id"], {
                "type": "retour produit dans stock livreur",
                "quantite": produit["quantite"],
                "manager_id": validated_data.get("manager_id")
            })
    else:
        for produit in produits:
            ProduitModel.increment_stock(
                produit_id=produit["produit_id"],
                quantite=produit["quantite"],
                acteur={"user_id": validated_data.get("manager_id")},
                type_mouvement="retour dans stock magasin"
            )

    # Mise à jour des produits livrés (quantités restantes)
    nouvelle_quantite = 0
    nouveau_montant_total = 0
    for key, q_retournee in total_retournes.items():
        produit_livre = produits_livres_dict[key]
        produit_livre["quantite"] = max(0, produit_livre["quantite"] - q_retournee)

    for p in produits_livres:
        nouvelle_quantite += p["quantite"]
        nouveau_montant_total += p["quantite"] * p["prix"]

    nouveau_montant_paye = min(livraison["montant_paye"], nouveau_montant_total)

    # Nouveau statut de paiement
    if nouveau_montant_paye == 0:
        statut_paiement = "non payé"
    elif 0 < nouveau_montant_paye < nouveau_montant_total:
        statut_paiement = "partiellement payé"
    else:
        statut_paiement = "payé"

    # Calcul final de la ristourne
    ancien_ristourne = livraison.get("ristourne", 0)
    ristourne_cumulee = ancien_ristourne  # initialiser avec l'existant

    if statut_paiement == "payé":
        ristourne_cumulee += montant_ristourne_retour
    elif statut_paiement == "partiellement payé":
        if montant_ristourne_retour > livraison["montant_paye"]:
            ristourne_cumulee +=  livraison["montant_paye"] - montant_ristourne_retour
        else:
            ristourne_cumulee = 0
    elif statut_paiement == "non payé":
        ristourne_cumulee = 0

    LivraisonModel.collection.update_one(
        {"_id": ObjectId(livraison_id)},
        {
            "$set": {
                "produits": produits_livres,
                "quantite": nouvelle_quantite,
                "montant_total": nouveau_montant_total,
                "montant_paye": nouveau_montant_paye,
                "ristourne": ristourne_cumulee,
                "have_ristourne": True,
                "statut_paiement": statut_paiement,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "message": "Retour enregistré avec succès",
        "retour_id": retour_id,
        "ristourne": ristourne_cumulee
    }, 201
"""

def creer_retour_livraison(data):
    """
    Crée un retour de livraison avec gestion dynamique de la ristourne,
    incluant le retour de conditionnements complets (quantite_conditionnement),
    sans casser le comportement existant.
    """
    try:
        schema = RetourLivraisonSchema()
        validated_data = schema.load(data)
    except ValidationError as err:
        return {"error": err.messages}, 400

    livraison_id = validated_data["livraison_id"]
    produits = validated_data["produits"]

    livraison = LivraisonModel.get_livraison_by_id(livraison_id)
    if not livraison:
        return {"error": "Livraison introuvable"}, 404

    produits_livres = livraison.get("produits", [])

    # Indexation des produits livrés
    produits_livres_dict = {}
    for p in produits_livres:
        key = (
            str(p["produit_id"]),
            str(p.get("conditionnement_id")) if p.get("is_conditionne") else "none"
        )
        produits_livres_dict[key] = p

    montant_ristourne_retour = 0
    total_retournes = {}

    for produit in produits:
        key = (
            str(produit["produit_id"]),
            str(produit.get("conditionnement_id")) if produit.get("is_conditionne") else "none"
        )
        produit_livre = produits_livres_dict.get(key)

        if not produit_livre:
            return {"error": f"Produit non trouvé dans la livraison (clé: {key})"}, 400

        # Nouveau : calcul de la quantité réelle à retourner
        quantite_retour = produit.get("quantite", 0)

        if "quantite_conditionnement" in produit:
            facteur = produit_livre.get("facteur", 1)
            quantite_retour += produit["quantite_conditionnement"] * facteur

        if quantite_retour <= 0:
            return {"error": f"Quantité retournée invalide pour le produit {produit['produit_id']}"}, 400

        quantite_livree = produit_livre["quantite"]
        deja_retournee = total_retournes.get(key, 0)

        if quantite_retour + deja_retournee > quantite_livree:
            return {
                "error": f"Retour impossible : la quantité ({quantite_retour}) dépasse la quantité livrée ({quantite_livree}) pour le produit {produit['produit_id']}"
            }, 400

        total_retournes[key] = deja_retournee + quantite_retour
        montant_ristourne_retour += produit_livre["prix"] * quantite_retour

    # Enregistrement du retour
    retour_id = RetourLivraisonModel.enregistrer_retour(validated_data)

    # Réintégration du stock
    if livraison.get("livreur_id") and not livraison.get("manager_id"):
        # On s'assure que chaque produit a bien une clé "quantite"
        for produit in produits:
            quantite = produit.get("quantite", 0)
            if "quantite_conditionnement" in produit:
                key = (
                    str(produit["produit_id"]),
                    str(produit.get("conditionnement_id")) if produit.get("is_conditionne") else "none"
                )
                facteur = produits_livres_dict[key].get("facteur", 1)
                quantite += produit["quantite_conditionnement"] * facteur
                produit["quantite"] = quantite  # Mise à jour de la quantité
       
        StockLivreurModel.ajouter_stock(validated_data["livreur_id"], produits)
        for produit in produits:
            ProduitModel.ajouter_mouvement_stock(produit["produit_id"], {
                "type": "retour produit dans stock livreur",
                "quantite": produit.get("quantite", 0),
                "manager_id": validated_data.get("manager_id")
            })
    else:
        for produit in produits:
            quantite = produit.get("quantite", 0)
            if "quantite_conditionnement" in produit:
                key = (
                    str(produit["produit_id"]),
                    str(produit.get("conditionnement_id")) if produit.get("is_conditionne") else "none"
                )
                facteur = produits_livres_dict[key].get("facteur", 1)
                quantite += produit["quantite_conditionnement"] * facteur

            ProduitModel.increment_stock(
                produit_id=produit["produit_id"],
                quantite=quantite,
                acteur={"user_id": validated_data.get("manager_id")},
                type_mouvement="retour dans stock magasin"
            )

    # Mise à jour des produits livrés
    nouvelle_quantite = 0
    nouveau_montant_total = 0
    for key, q_retournee in total_retournes.items():
        produit_livre = produits_livres_dict[key]
        produit_livre["quantite"] = max(0, produit_livre["quantite"] - q_retournee)

    for p in produits_livres:
        nouvelle_quantite += p["quantite"]
        nouveau_montant_total += p["quantite"] * p["prix"]

    nouveau_montant_paye = min(livraison["montant_paye"], nouveau_montant_total)

    # Nouveau statut de paiement
    if nouveau_montant_paye == 0:
        statut_paiement = "non payé"
    elif 0 < nouveau_montant_paye < nouveau_montant_total:
        statut_paiement = "partiellement payé"
    else:
        statut_paiement = "payé"

    # Calcul de la ristourne
    ancien_ristourne = livraison.get("ristourne", 0)
    ristourne_cumulee = ancien_ristourne

    if statut_paiement == "payé":
        ristourne_cumulee += montant_ristourne_retour
    elif statut_paiement == "partiellement payé":
        if montant_ristourne_retour > livraison["montant_paye"]:
            ristourne_cumulee += livraison["montant_paye"] - montant_ristourne_retour
        else:
            ristourne_cumulee = 0
    elif statut_paiement == "non payé":
        ristourne_cumulee = 0

    LivraisonModel.collection.update_one(
        {"_id": ObjectId(livraison_id)},
        {
            "$set": {
                "produits": produits_livres,
                "quantite": nouvelle_quantite,
                "montant_total": nouveau_montant_total,
                "montant_paye": nouveau_montant_paye,
                "retour": ristourne_cumulee,
                "have_retour": True,
                "statut_paiement": statut_paiement,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "message": "Retour enregistré avec succès",
        "retour_id": retour_id,
        "montant_retour": ristourne_cumulee
    }, 201


 
    
# service permettant de rembourser un retour
def rembourser_ristourne_client(livraison_id):
    """
    Rembourse la ristourne accordée à un client pour une livraison donnée.
    """
    livraison = LivraisonModel.collection.find_one({"_id": ObjectId(livraison_id)})

    if not livraison:
        return {"error": "Livraison introuvable"}, 404

    retour = livraison.get("retour", 0)
    if retour <= 0:
        return {"error": "Aucun retour à rembourser"}, 400

    if not livraison.get("have_retour") or livraison.get("have_retour") is False:
        return {"error": "Le retour a déjà été remboursé"}, 400

    # Exemple : tu peux ici créer une ligne dans un historique ou envoyer une notification

    # Effectuer le remboursement (à adapter selon la logique métier, caisse, ou solde)
    # Ici on met juste à jour l'état
    LivraisonModel.collection.update_one(
        {"_id": ObjectId(livraison_id)},
        {
            "$set": {
                "have_retour": False,
                "retour": 0,  # On remet le retour à 0
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {"message": "Retour remboursé avec succès", "status": 200}


# Service permettant de rembourser le relicat d'un client

def rembourser_service(livraison_id):
    try:
        result = LivraisonModel.rembourser(livraison_id)
        result2 = rembourser_ristourne_client(livraison_id)
        return result2
    except Exception as e:
        return {"message": f"Erreur lors du remboursemen client : {str(e)}", "status": 500}
    