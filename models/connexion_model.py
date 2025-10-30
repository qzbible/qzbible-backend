from datetime import datetime
from bson import ObjectId
from extensions import mongo

class ConnexionModel:
    collection = mongo.db.connexions  # nom de la collection MongoDB pour les connexions

    @staticmethod
    def create_connexion(data: dict):
        """
        Enregistre une nouvelle connexion utilisateur en base.

        data doit contenir au minimum :
        - user_id (ObjectId ou str)
        - email (str)
        - role (str)
        - church_id (ObjectId ou str ou None)
        - timestamp (datetime)
        - ip_address (str)

        Cette méthode insère un document dans la collection 'connexions'.
        """
        # Assurer que user_id et magasin_id sont des ObjectId si ce sont des chaînes
        if "user_id" in data and not isinstance(data["user_id"], ObjectId):
            try:
                data["user_id"] = ObjectId(data["user_id"])
            except Exception:
                pass  # si conversion impossible, on laisse tel quel (ou raise)

        if "church_id" in data and data["church_id"]:
            if not isinstance(data["church_id"], ObjectId):
                try:
                    data["church_id"] = ObjectId(data["church_id"])
                except Exception:
                    data["church_id"] = None

        # Vérifier la présence d'un timestamp, sinon mettre maintenant
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow()

        # Insérer dans la base
        result = ConnexionModel.collection.insert_one(data)
        return str(result.inserted_id)
    
    
    
    
    @staticmethod
    def get_connexions_par_periode(granularite: str):
        """
        Récupère les connexions, groupées par période (jour/semaine/mois/année).
        Retourne une liste de documents avec 'periode' et 'count'.
        """
        pipeline = []

        # Étape 1 : Projeter un champ 'periode' selon granularité
        if granularite == "jour":
            pipeline.append({
                "$project": {
                    "periode": { 
                        "$dateToString": { "format": "%Y-%m-%d", "date": "$created_at" }
                    }
                }
            })
        elif granularite == "semaine":
            pipeline.append({
                "$project": {
                    "year": { "$isoWeekYear": "$created_at" },
                    "week": { "$isoWeek": "$created_at" }
                }
            })
            pipeline.append({
                "$project": {
                    "periode": { 
                        "$concat": [
                            { "$toString": "$year" },
                            "-W",
                            { 
                                "$cond": [
                                    { "$lt": [ "$week", 10 ] },
                                    { "$concat": ["0", { "$toString": "$week" }] },
                                    { "$toString": "$week" }
                                ]
                            }
                        ]
                    }
                }
            })
        elif granularite == "mois":
            pipeline.append({
                "$project": {
                    "periode": { 
                        "$dateToString": { "format": "%Y-%m", "date": "$created_at" }
                    }
                }
            })
        elif granularite == "annee":
            pipeline.append({
                "$project": {
                    "periode": { 
                        "$dateToString": { "format": "%Y", "date": "$created_at" }
                    }
                }
            })
        else:
            raise ValueError("Granularité invalide")

        # Étape 2 : Grouper par période et compter
        pipeline.append({
            "$group": {
                "_id": "$periode",
                "count": {"$sum": 1}
            }
        })

        # Étape 3 : Trier par période
        pipeline.append({
            "$sort": {"_id": 1}
        })

        results = list(ConnexionModel.collection.aggregate(pipeline))
        return [{"periode": r["_id"], "count": r["count"]} for r in results]

    @staticmethod
    def get_all():
        """
        Récupère toutes les connexions.
        Retourne une liste de documents de connexions.
        """
        return list(ConnexionModel.collection.find())