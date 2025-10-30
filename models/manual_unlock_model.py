# models/manual_unlock_model.py

from bson import ObjectId
from datetime import datetime
from extensions import mongo

class ManualUnlockModel:
    
    collection = mongo.db.manual_unlocks
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.manual_unlocks
    
    @staticmethod
    def create_unlock(data):
        """
        Crée un enregistrement de déblocage manuel.
        
        :param data: dict contenant les informations du déblocage
        :return: dict contenant le message de succès et l'ID
        """
        unlock = {
            "church_id": ObjectId(data["church_id"]),
            "learner_id": ObjectId(data["learner_id"]),
            "chapter_id": ObjectId(data["chapter_id"]),
            "unlocked_by": ObjectId(data["unlocked_by"]),
            "reason": data.get("reason", "Déblocage manuel par le leader"),
            "created_at": datetime.utcnow()
        }
        
        result = ManualUnlockModel.get_collection().insert_one(unlock)
        
        return {
            "message": "Déblocage enregistré avec succès",
            "unlock_id": str(result.inserted_id)
        }
    
    @staticmethod
    def get_unlock_by_id(unlock_id):
        """
        Récupère un déblocage par son ID.
        """
        unlock = ManualUnlockModel.get_collection().find_one({"_id": ObjectId(unlock_id)})
        if unlock:
            unlock["_id"] = str(unlock["_id"])
            unlock["church_id"] = str(unlock["church_id"])
            unlock["learner_id"] = str(unlock["learner_id"])
            unlock["chapter_id"] = str(unlock["chapter_id"])
            unlock["unlocked_by"] = str(unlock["unlocked_by"])
        
        return unlock
    
    @staticmethod
    def get_unlocks_by_learner(learner_id, church_id=None):
        """
        Récupère tous les déblocages d'un apprenant.
        """
        query = {"learner_id": ObjectId(learner_id)}
        if church_id:
            query["church_id"] = ObjectId(church_id)
        
        unlocks = ManualUnlockModel.get_collection().find(query).sort("created_at", -1)
        return list(unlocks)
    
    @staticmethod
    def get_unlocks_by_chapter(chapter_id, church_id=None):
        """
        Récupère tous les déblocages pour un chapitre.
        """
        query = {"chapter_id": ObjectId(chapter_id)}
        if church_id:
            query["church_id"] = ObjectId(church_id)
        
        unlocks = ManualUnlockModel.get_collection().find(query).sort("created_at", -1)
        return list(unlocks)
    
    @staticmethod
    def get_unlocks_by_leader(unlocked_by, church_id=None):
        """
        Récupère tous les déblocages effectués par un leader.
        """
        query = {"unlocked_by": ObjectId(unlocked_by)}
        if church_id:
            query["church_id"] = ObjectId(church_id)
        
        unlocks = ManualUnlockModel.get_collection().find(query).sort("created_at", -1)
        return list(unlocks)
    
    @staticmethod
    def get_all_unlocks_by_church(church_id, filters=None):
        """
        Récupère tous les déblocages d'une église avec filtres optionnels.
        """
        query = {"church_id": ObjectId(church_id)}
        
        if filters:
            if filters.get("learner_id"):
                query["learner_id"] = ObjectId(filters["learner_id"])
            if filters.get("chapter_id"):
                query["chapter_id"] = ObjectId(filters["chapter_id"])
            if filters.get("unlocked_by"):
                query["unlocked_by"] = ObjectId(filters["unlocked_by"])
            if filters.get("start_date"):
                query["created_at"] = {"$gte": filters["start_date"]}
            if filters.get("end_date"):
                if "created_at" in query:
                    query["created_at"]["$lte"] = filters["end_date"]
                else:
                    query["created_at"] = {"$lte": filters["end_date"]}
        
        unlocks = ManualUnlockModel.get_collection().find(query).sort("created_at", -1)
        return list(unlocks)
    
    @staticmethod
    def count_unlocks_by_learner(learner_id, church_id=None):
        """
        Compte le nombre de déblocages pour un apprenant.
        """
        query = {"learner_id": ObjectId(learner_id)}
        if church_id:
            query["church_id"] = ObjectId(church_id)
        
        return ManualUnlockModel.get_collection().count_documents(query)
    
    @staticmethod
    def count_unlocks_by_leader(unlocked_by, church_id=None):
        """
        Compte le nombre de déblocages effectués par un leader.
        """
        query = {"unlocked_by": ObjectId(unlocked_by)}
        if church_id:
            query["church_id"] = ObjectId(church_id)
        
        return ManualUnlockModel.get_collection().count_documents(query)
    
    @staticmethod
    def check_if_manually_unlocked(learner_id, chapter_id):
        """
        Vérifie si un chapitre a été débloqué manuellement pour un apprenant.
        """
        unlock = ManualUnlockModel.get_collection().find_one({
            "learner_id": ObjectId(learner_id),
            "chapter_id": ObjectId(chapter_id)
        })
        return unlock is not None
    
    @staticmethod
    def delete_unlock(unlock_id):
        """
        Supprime un enregistrement de déblocage.
        """
        result = ManualUnlockModel.get_collection().delete_one({"_id": ObjectId(unlock_id)})
        
        return {
            "message": "Déblocage supprimé avec succès",
            "deleted_count": result.deleted_count
        }
    
    @staticmethod
    def get_unlock_stats_by_church(church_id):
        """
        Récupère les statistiques de déblocage pour une église.
        """
        pipeline = [
            {"$match": {"church_id": ObjectId(church_id)}},
            {"$group": {
                "_id": None,
                "total_unlocks": {"$sum": 1},
                "unique_learners": {"$addToSet": "$learner_id"},
                "unique_leaders": {"$addToSet": "$unlocked_by"}
            }},
            {"$project": {
                "_id": 0,
                "total_unlocks": 1,
                "unique_learners_count": {"$size": "$unique_learners"},
                "unique_leaders_count": {"$size": "$unique_leaders"}
            }}
        ]
        
        result = list(ManualUnlockModel.get_collection().aggregate(pipeline))
        return result[0] if result else {
            "total_unlocks": 0,
            "unique_learners_count": 0,
            "unique_leaders_count": 0
        }
    
    @staticmethod
    def get_most_unlocked_chapters(church_id, limit=10):
        """
        Récupère les chapitres les plus souvent débloqués manuellement.
        """
        pipeline = [
            {"$match": {"church_id": ObjectId(church_id)}},
            {"$group": {
                "_id": "$chapter_id",
                "unlock_count": {"$sum": 1},
                "unique_learners": {"$addToSet": "$learner_id"}
            }},
            {"$project": {
                "chapter_id": "$_id",
                "unlock_count": 1,
                "unique_learners_count": {"$size": "$unique_learners"},
                "_id": 0
            }},
            {"$sort": {"unlock_count": -1}},
            {"$limit": limit}
        ]
        
        return list(ManualUnlockModel.get_collection().aggregate(pipeline))
    
    @staticmethod
    def get_most_active_leaders(church_id, limit=10):
        """
        Récupère les leaders qui débloquent le plus souvent.
        """
        pipeline = [
            {"$match": {"church_id": ObjectId(church_id)}},
            {"$group": {
                "_id": "$unlocked_by",
                "unlock_count": {"$sum": 1},
                "unique_learners": {"$addToSet": "$learner_id"}
            }},
            {"$project": {
                "leader_id": "$_id",
                "unlock_count": 1,
                "unique_learners_count": {"$size": "$unique_learners"},
                "_id": 0
            }},
            {"$sort": {"unlock_count": -1}},
            {"$limit": limit}
        ]
        
        return list(ManualUnlockModel.get_collection().aggregate(pipeline))