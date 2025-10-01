from bson import ObjectId
from datetime import datetime
from extensions import mongo
import os

class ProduitModel:
    
    
    @staticmethod
    def get_collection():
        return mongo.db.produits
    
    collection = mongo.db.produits
    
    @staticmethod
    def create_produit(data, image_filename=None):
        quantite = int(data["quantite"])
        
        #  Vérifier si un produit avec le même nom existe déjà dans ce magasin
        produit_existant = ProduitModel.get_collection().find_one({
            "nom": data["nom"],
            "magasin_id": ObjectId(data["magasin_id"])
        })
        if produit_existant:
            return {
                "error": "Ce produit existe déjà dans ce magasin"
            }, 409  # 409 Conflict

        prix_unitaire = float(data["prix"])
        
        # Traitemnt des conditionnements si existant
        conditionnement_nettoyes = []
        for c in data.get("conditionnements", []):
            try:
                nom = c["nom"]
                facteur = int(c["facteur"])
            except (KeyError, ValueError):
                continue 
            
            prix_reference = facteur * prix_unitaire
            prix_conditionnement = float(c["prix_conditionnement"]) if c.get("prix_conditionnement") else prix_reference    
            economie = prix_conditionnement - prix_reference    
            
            conditionnement_nettoyes.append({
                "_id": ObjectId(),
                "nom": nom,
                "facteur": facteur,
                "prix_conditionnement": prix_conditionnement,
                "prix_reference": prix_reference,
                "economie": economie
            })
            
        
        produit = {
            "nom": data["nom"],
            "description": data.get("description", ""),
            "image": image_filename,
            "prix": float(data["prix"]),
            "unite": data["unite"],  # e.g., "kg", "litre"
            "quantite": quantite,
            "quantite_initiale": quantite,  # pour traçabilité/statistique
            "etat": "en stock" if quantite > 0 else "en rupture",
            "categorie_id": ObjectId(data["categorie_id"]),
            "magasin_id": ObjectId(data["magasin_id"]),
            "mouvements_stock": [],  # traçabilité des mouvements
            "conditionnements": conditionnement_nettoyes,  # conditionnements
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()  #
            
        }
        result = ProduitModel.get_collection().insert_one(produit)
        return str(result.inserted_id)
    
    
    # Récupérer tous les produits d'un magasin   
    @staticmethod
    def get_all_by_magasin(magasin_id):
        return list(ProduitModel.get_collection().find({"magasin_id": ObjectId(magasin_id)}))


    @staticmethod
    def get_conditionnement_by_id(produit_id, conditionnement_id):
        """
        Récupère un conditionnement spécifique à partir de son ID pour un produit donné.
        """
        produit = ProduitModel.get_collection().find_one({"_id": ObjectId(produit_id)})
        if not produit:
            return None

        for cond in produit.get("conditionnements", []):
            if str(cond["_id"]) == str(conditionnement_id):
                return cond

        return None


    @staticmethod
    def get_by_id(produit_id):
        if not isinstance(produit_id, ObjectId):
            try:
                produit_id = ObjectId(produit_id)
            except Exception as e:
                print(f"Erreur de conversion en ObjectId : {e}")
                return None
        result = ProduitModel.get_collection().find_one({"_id": produit_id})
        
        return result



        # Mettre à jour un produit
    @staticmethod
    def update_produit(produit_id, data):
        update_data = {k: data[k] for k in data if k in ["nom", "description", "prix", "unite", "quantite", "categorie_id", "image"]}

        # Quantité et état
        if "quantite" in update_data:
            update_data["etat"] = "en stock" if int(update_data["quantite"]) > 0 else "en rupture"
            update_data["quantite"] = int(update_data["quantite"])
            # retirer quantite dans le dictionnaire pour éviter les doublons
            if "quantite" in update_data:
                del update_data["quantite"]
            
        # Prix
        if "prix" in update_data:
            update_data["prix"] = float(update_data["prix"])

        # Catégorie
        if "categorie_id" in update_data:
            update_data["categorie_id"] = ObjectId(update_data["categorie_id"])

        # Conditionnements
        if "conditionnements" in data:
            try:
                produit_actuel = ProduitModel.get_by_id(produit_id)
                anciens_conditionnements = produit_actuel.get("conditionnements", [])

                # Normaliser les anciens conditionnements : leur attribuer un _id s'il manque
                for cond in anciens_conditionnements:
                    if "_id" not in cond:
                        cond["_id"] = ObjectId()

                ancien_map = {str(cond["_id"]): cond for cond in anciens_conditionnements}
                prix_unitaire = float(data.get("prix", produit_actuel["prix"]))
                nouveaux_conditionnements = []
                ids_recus = set()

                for cond in data["conditionnements"]:
                    nom = cond["nom"]
                    facteur = int(cond["facteur"])
                    prix_reference = facteur * prix_unitaire
                    prix_conditionnement = float(cond.get("prix_conditionnement", prix_reference))
                    economie = prix_conditionnement - prix_reference

                    if "_id" in cond:
                        id_str = str(cond["_id"])
                        ids_recus.add(id_str)
                        nouveaux_conditionnements.append({
                            "_id": ObjectId(id_str),
                            "nom": nom,
                            "facteur": facteur,
                            "prix_conditionnement": prix_conditionnement,
                            "prix_reference": prix_reference,
                            "economie": economie
                        })
                    else:
                        new_id = ObjectId()
                        nouveaux_conditionnements.append({
                            "_id": new_id,
                            "nom": nom,
                            "facteur": facteur,
                            "prix_conditionnement": prix_conditionnement,
                            "prix_reference": prix_reference,
                            "economie": economie
                        })

                # Supprimer les anciens conditionnements qui n'ont pas été renvoyés par le frontend
                # Cela évite les doublons
                update_data["conditionnements"] = [
                    cond for cond in nouveaux_conditionnements
                ]

            except Exception as e:
                print("Erreur lors de la mise à jour des conditionnements :", e)

        # Mise à jour MongoDB
        return ProduitModel.get_collection().find_one_and_update(
            {"_id": ObjectId(produit_id)},
            {"$set": update_data}
        )






    # Supprimer un produit et son image associée
    @staticmethod
    def delete_produit(produit_id):
        produit = ProduitModel.get_collection().find_one_and_delete({"_id": ObjectId(produit_id)})
        if produit and produit.get("image"):
            image_path = os.path.join("uploads", produit["image"])
            if os.path.exists(image_path):
                os.remove(image_path)
        return produit



    #  Traçabilité des mouvements
    @staticmethod
    def ajouter_mouvement_stock(produit_id, mouvement):
        ProduitModel.get_collection().update_one(
            {"_id": ObjectId(produit_id)},
            {"$push": {"mouvements_stock": {
                **mouvement,
                "date": datetime.utcnow()
            }}}
        )



    #  Décrémenter stock + tracer mouvement
    @staticmethod
    def decrement_stock(produit_id, quantite, acteur=None, type_mouvement="sortie"):
        produit = ProduitModel.get_collection().find_one({"_id": ObjectId(produit_id)})
        if not produit:
            return None

        nouvelle_quantite = produit["quantite"] - quantite
        etat = "en stock" if nouvelle_quantite > 0 else "en rupture"

        ProduitModel.get_collection().update_one(
            {"_id": ObjectId(produit_id)},
            {"$set": {"quantite": nouvelle_quantite, "etat": etat}}
        )

        ProduitModel.ajouter_mouvement_stock(produit_id, {
            "type": type_mouvement,
            "quantite": -quantite,
            **(acteur or {})  # admin_id, manager_id, livreur_id, etc.
        })

        return ProduitModel.get_by_id(produit_id)

    # Incrémenter stock + tracer mouvement
    @staticmethod
    def increment_stock(produit_id, quantite, acteur=None, type_mouvement="entrée"):
        produit = ProduitModel.get_collection().find_one({"_id": ObjectId(produit_id)})
        if not produit:
            return None

        nouvelle_quantite = produit["quantite"] + quantite

        ProduitModel.get_collection().update_one(
            {"_id": ObjectId(produit_id)},
            {"$set": {"quantite": nouvelle_quantite, "etat": "en stock"}}
        )

        ProduitModel.ajouter_mouvement_stock(produit_id, {
            "type": type_mouvement,
            "quantite": quantite,
            **(acteur or {})  # admin_id, manager_id, etc.
        })

        return ProduitModel.get_by_id(produit_id)

    
    #  Récupérer les mouvements de stock d'un produit
    @staticmethod
    def get_mouvements_stock(produit_id):
        produit = ProduitModel.get_by_id(produit_id)
        if produit:
            return produit.get("mouvements_stock", [])
        return []



    # Supprimer les mouvements de stock d'un produit
    @staticmethod
    def delete_mouvements_stock(produit_id):
        """
        Supprime tous les mouvements de stock d'un produit.
        """
        result = ProduitModel.get_collection().update_one(
            {"_id": ObjectId(produit_id)},
            {"$unset": {"mouvements_stock": ""}}
        )
        return result.modified_count > 0
    
    
    
    
    # Récupérer les produits d'une catégorie
    @staticmethod
    def get_by_categorie(categorie_id):
        return list(ProduitModel.get_collection().find({"categorie_id": ObjectId(categorie_id)}))



    # Récupérer une liste de produits à partir d'une liste d'IDs
    @staticmethod
    def get_produits_by_ids(produit_ids):
        """
        Récupère une liste de produits à partir d'une liste d'IDs (str).
        """
        # Conversion en ObjectId si nécessaire
        try:
            object_ids = [ObjectId(pid) for pid in produit_ids]
        except Exception:
            object_ids = produit_ids  # au cas où les IDs sont déjà strings utilisables

        # Requête MongoDB
        produits = ProduitModel.get_collection().find({ "_id": { "$in": object_ids } })

        # Convertir les documents en dictionnaires Python
        return list(produits)

    
    
    # Methode permettant d'importer ou de créer des produits provenant d'un fichier excel
    @staticmethod
    def create_from_excel(row, magasin_id, categorie_id):
        produit = {
            "nom": row["nom"],
            "description": row.get("description", ""),
            "prix": row["prix"],
            "unite": row["unite"],
            "quantite": row["quantite"],
            "quantite_initiale": row["quantite"],
            "etat": "en stock" if row["quantite"] > 0 else "en rupture",
            "categorie_id": ObjectId(categorie_id),
            "magasin_id": ObjectId(magasin_id),
            "mouvements_stock": [],
            "conditionnements": [],
            "created_at": datetime.utcnow()
        }
        return ProduitModel.get_collection().insert_one(produit)


    @staticmethod
    def approvisionner_produit(produit_id, quantite, acteur):
        produit = ProduitModel.get_collection().find_one({"_id": ObjectId(produit_id)})
        if not produit:
            return None

        nouvelle_quantite = produit["quantite"] + quantite

        # Ajout du mouvement dans la liste
        mouvement = {
            "type": "approvisionnement",
            "quantite": quantite,
            "date": datetime.utcnow(),
            "acteur": acteur
        }

        ProduitModel.get_collection().update_one(
            {"_id": ObjectId(produit_id)},
            {
                "$set": {
                    "quantite": nouvelle_quantite,
                    "etat": "en stock"
                },
                "$push": {
                    "mouvements_stock": mouvement
                }
            }
        )

        return ProduitModel.get_by_id(produit_id)