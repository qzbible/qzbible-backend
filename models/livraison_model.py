# models/livraison_model.py

from bson import ObjectId
from datetime import datetime
from extensions import mongo
from utils.inject_magasin_id import inject_magasin_id  # Ajouté
from services.notification_service import notifier_manager_ristourne  # Ajouté
class LivraisonModel:
    #
    
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.livraisons
    
    collection = mongo.db.livraisons
    
    @staticmethod
    def create_livraison(data, produits):
        """
        Enregistre une livraison avec ou sans conditionnement.
        """
        try:
            data = inject_magasin_id(data)
        except Exception as e:
            return {"error": str(e)}, 401

        montant_total = 0
        quantite_totale = 0
        print(data)

        # Calcul du montant total et de la quantité
        for produit in produits:
            quantite = int(produit["quantite"])
            prix_unitaire = float(produit["prix"])
            montant_total += quantite * prix_unitaire
            quantite_totale += quantite

        montant_paye = float(data.get("montant_paye", montant_total))
        relicat = data.get("relicat", 0)
        ristourne = data.get("ristourne", 0.0)
        have_ristourne = False
        print("Montant total:", montant_total)
        print("Montant payé:", montant_paye)
        print("action_manager:", data.get("action_manager"))
        # Détermination du statut de paiement
        if montant_paye == 0 and data.get("statut_paiement") != "payé":
            statut_paiement = "non payé"
        elif 0 < montant_paye < montant_total:
            if data.get("action_manager") == True:
                ristourne = montant_total - montant_paye
                have_ristourne = True
                statut_paiement = "partiellement payé" 
            else:
                statut_paiement = "partiellement payé"
        else:
            statut_paiement = "payé"
            montant_paye = montant_total


        # Détermination du statut de livraison initial
        statut_livraison = "en cours" if statut_paiement != "payé" else "livrée"

        # recupérer l'utilisateur et vérifierson role
        
        manager_id = ObjectId(data["manager_id"]) if data.get("manager_id") else None
        livreur_id = ObjectId(data["livreur_id"]) if data.get("livreur_id") else None
        livraison = {
            "livreur_id": livreur_id,
            "manager_id": manager_id,
            "magasin_id": ObjectId(data["magasin_id"]),
            "client_id": ObjectId(data["client_id"]),
            "produits": produits,
            "montant_total": montant_total,
            "montant_paye": montant_paye,
            "quantite": quantite_totale,
            "statut_paiement": statut_paiement,
            "statut_livraison": statut_livraison,
            "date_commande": datetime.utcnow(),
            "date_livraison": datetime.utcnow(),
            "relicat": relicat,
            "ristourne": ristourne,
            "retour": 0.0,  # Montant du retour
            "have_ristourne": have_ristourne,
            "have_retour": False,
            "action_manager": False,  # Indique si le manager a validé la livraison
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = LivraisonModel.get_collection().insert_one(livraison)
        if livraison["have_ristourne"]:
            notifier_manager_ristourne(result.inserted_id, livraison["client_id"], livraison["livreur_id"], livraison["montant_total"], livraison["montant_paye"], livraison["ristourne"], livraison["created_at"])
        return str(result.inserted_id)


    @staticmethod
    def get_livraison_by_id(livraison_id):
        return LivraisonModel.get_collection().find_one({"_id": ObjectId(livraison_id)})

    @staticmethod
    def get_livraisons_by_livreur(livreur_id):
        return list(LivraisonModel.get_collection().find({"livreur_id": ObjectId(livreur_id)}))

    @staticmethod
    def rembourser(livraison_id):
        result = LivraisonModel.collection.update_one(
            {"_id" : ObjectId(livraison_id)},
            {"$set" : {"relicat" : 0}}
        )
        if result.modified_count > 0:
            return {"message" : "Remboursement client terminé avec succès"}
        else:
            return {"message" : "Aucune mise à jour effectuée."}
        
       

    @staticmethod
    def get_all_livraisons(magasin_id=None):
        if magasin_id is None:
            try:
                data = inject_magasin_id({})
                magasin_id = data["magasin_id"]
            except Exception as e:
                return {"error": str(e)}, 401
        return list(LivraisonModel.get_collection().find({"magasin_id": ObjectId(magasin_id)}))

       
    @staticmethod
    def get_all_livraisons_plateforme():
        """
        Retourne toutes les livraisons de la plateforme, sans filtrer par magasin.
        """
        try:
            return list(LivraisonModel.get_collection().find())
        except Exception as e:
            print(f"[ERREUR] Échec de récupération des livraisons plateforme : {e}")
            return []


    @staticmethod
    def update_livraison(livraison_id, data):
        update_data = {k: data[k] for k in data if k in ["statut_paiement", "statut_livraison", "date_livraison"]}
        update_data["updated_at"] = datetime.utcnow()

        return LivraisonModel.get_collection().find_one_and_update(
            {"_id": ObjectId(livraison_id)},
            {"$set": update_data}
        )

    @staticmethod
    def delete_livraison(livraison_id):
        return LivraisonModel.get_collection().find_one_and_delete({"_id": ObjectId(livraison_id)})

    @staticmethod
    def get_livraison_for_admin_or_manager(manager_id):
        return list(LivraisonModel.get_collection().find({"manager_id": ObjectId(manager_id)}))

    @staticmethod
    def get_livraisons_between_dates(start_date, end_date, livreur_id=None, magasin_id=None):
        query = {
            "date_livraison": {"$gte": start_date, "$lte": end_date}
        }
        if livreur_id:
            query["livreur_id"] = ObjectId(livreur_id)
        if magasin_id is None:
            try:
                data = inject_magasin_id({})
                magasin_id = data["magasin_id"]
            except Exception as e:
                return {"error": str(e)}, 401
        query["magasin_id"] = ObjectId(magasin_id)
        return list(LivraisonModel.get_collection().find(query))

    @staticmethod
    def ajouter_paiement(livraison_id, montant):
        livraison = LivraisonModel.get_collection().find_one({"_id": ObjectId(livraison_id)})
        if not livraison:
            return None

        if livraison.get("montant_paye", 0) >= livraison["montant_total"]:
            return {"message": "Le montant payé est déjà égal au montant total."}

        nouveau_montant_paye = livraison.get("montant_paye", 0) + montant
        montant_total = livraison["montant_total"]

        if nouveau_montant_paye == 0:
            statut_paiement = "non payé"
        elif 0 < nouveau_montant_paye < montant_total:
            statut_paiement = "partiellement payé"
        else:
            statut_paiement = "payé"

        statut_livraison = livraison["statut_livraison"]
        if statut_paiement == "payé":
            statut_livraison = "livrée"

        update_data = {
            "montant_paye": nouveau_montant_paye,
            "statut_paiement": statut_paiement,
            "statut_livraison": statut_livraison,
            "updated_at": datetime.utcnow()
        }

        return LivraisonModel.get_collection().find_one_and_update(
            {"_id": ObjectId(livraison_id)},
            {"$set": update_data},
            return_document=True
        )
        
 

    @staticmethod
    def ajouter_ristourne(livraison_id, montant_ristourne):
        livraison = LivraisonModel.get_collection().find_one({"_id": ObjectId(livraison_id)})
        ancien_montant_paye = livraison.get("montant_paye", 0)
        ancien_montant_total = livraison.get("montant_total", 0)

        LivraisonModel.get_collection().update_one(
            {"_id": ObjectId(livraison_id)},
            {
                "$inc": {
                    "ristourne": montant_ristourne,
                    "montant_paye": -montant_ristourne,
                    "montant_total": -montant_ristourne
                },
                "$set": {
                    "updated_at": datetime.utcnow(),
                    "have_ristourne": True
                }
            }
        )
    # validation d'une ristourne par le manager
    @staticmethod
    def valider_ristourne(livraison_id, manager_id):
        from datetime import datetime

        collection = LivraisonModel.get_collection()

        # Récupérer la livraison
        livraison = collection.find_one({"_id": ObjectId(livraison_id)})
        print("Livraison trouvée :", livraison)
        if not livraison:
            return False

        montant_paye = livraison.get("montant_paye", 0.0)

        # Mettre à jour les champs nécessaires
        result = collection.update_one(
            {"_id": ObjectId(livraison_id)},
            {
                "$set": {
                    "statut_paiement": "payé",
                    "statut_livraison": "livrée",
                    "action_manager": False,
                    "ristourne": 0.0,
                    "montant_total": montant_paye,
                    "manager_id": ObjectId(manager_id),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

        
