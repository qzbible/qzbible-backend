# models/simple_reading_plan_model.py

from bson import ObjectId
from datetime import datetime
from extensions import mongo

class SimpleReadingPlanModel:
    
    collection = mongo.db.simple_reading_plans
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.simple_reading_plans
    
    @staticmethod
    def create_plan(data):
        """Créer un plan de lecture simple"""
        plan = {
            "title": data["title"],
            "subtitle": data["subtitle"],
            "description": data["description"],
            "user_id" : data["user_id"],
            "settings": {
                "duration_months": data["duration_months"],
                "daily_chapters": data["daily_chapters"],
                "has_notifications": data.get("has_notifications", True),
                "auto_save_progress": data.get("auto_save_progress", True)
            },
            "content": {
                "book_focus": data["book_focus"],
                "reading_schedule": data["reading_schedule"]
            },
            "meta": {
                "emoji": data.get("emoji", "📖"),
                "color": data.get("color", "#2196F3"),
                "created_at": datetime.utcnow(),
                "is_template": data.get("is_template", True),
                "creator_type": data.get("creator_type", "system")
            },
            "stats": {
                "subscribers": 0,
                "completions": 0,
                "avg_rating": 0.0
            }
        }
        
        result = SimpleReadingPlanModel.get_collection().insert_one(plan)
        
        return {
            "message": "Plan de lecture créé avec succès",
            "plan_id": str(result.inserted_id)
        }
    
    @staticmethod
    def get_plan_by_id(plan_id):
        """Récupérer un plan par ID"""
        plan = SimpleReadingPlanModel.get_collection().find_one({"_id": ObjectId(plan_id)})
        if plan:
            plan["_id"] = str(plan["_id"])
        return plan
    
    @staticmethod
    def get_all_plans(filters=None, skip=0, limit=20):
        """Récupérer tous les plans avec filtres"""
        query = {}
        
        if filters:
            if filters.get("book_focus"):
                query["content.book_focus"] = {"$in": filters["book_focus"]}
            if filters.get("duration_months"):
                query["settings.duration_months"] = filters["duration_months"]
            if filters.get("search"):
                query["$or"] = [
                    {"title": {"$regex": filters["search"], "$options": "i"}},
                    {"subtitle": {"$regex": filters["search"], "$options": "i"}},
                    {"description": {"$regex": filters["search"], "$options": "i"}}
                ]
        
        plans = SimpleReadingPlanModel.get_collection().find(query).sort("meta.created_at", -1).skip(skip).limit(limit)
        return list(plans)
    
    @staticmethod
    def count_plans(filters=None):
        """Compter les plans avec filtres"""
        query = {}
        
        if filters:
            if filters.get("book_focus"):
                query["content.book_focus"] = {"$in": filters["book_focus"]}
            if filters.get("duration_months"):
                query["settings.duration_months"] = filters["duration_months"]
            if filters.get("search"):
                query["$or"] = [
                    {"title": {"$regex": filters["search"], "$options": "i"}},
                    {"subtitle": {"$regex": filters["search"], "$options": "i"}},
                    {"description": {"$regex": filters["search"], "$options": "i"}}
                ]
        
        return SimpleReadingPlanModel.get_collection().count_documents(query)
    
    @staticmethod
    def update_stats(plan_id, action):
        """Mettre à jour les statistiques du plan"""
        update_data = {}
        if action == "subscribe":
            update_data = {"$inc": {"stats.subscribers": 1}}
        elif action == "complete":
            update_data = {"$inc": {"stats.completions": 1}}
        
        if update_data:
            SimpleReadingPlanModel.get_collection().update_one(
                {"_id": ObjectId(plan_id)},
                update_data
            )


class UserSimplePlanModel:
    """Modèle pour les inscriptions utilisateur aux plans simples"""
    
    collection = mongo.db.user_simple_plans
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.user_simple_plans
    
    @staticmethod
    def create_subscription(data):
        """Créer une inscription à un plan simple"""
        # Vérifier si déjà inscrit
        existing = UserSimplePlanModel.get_collection().find_one({
            "user_id": ObjectId(data["user_id"]),
            "plan_id": ObjectId(data["plan_id"]),
            "status": "active"
        })
        
        if existing:
            return {"message": "Utilisateur déjà inscrit à ce plan"}, 400
        
        subscription = {
            "user_id": ObjectId(data["user_id"]),
            "plan_id": ObjectId(data["plan_id"]),
            "progress": {
                "current_day": 1,
                "completed_days": [],
                "started_at": datetime.utcnow(),
                "last_reading": None,
                "completion_percentage": 0
            },
            "preferences": {
                "reminder_time": data.get("reminder_time", "07:00"),
                "reminder_enabled": data.get("reminder_enabled", True)
            },
            "status": "active",
            "created_at": datetime.utcnow()
        }
        
        result = UserSimplePlanModel.get_collection().insert_one(subscription)
        
        # Mettre à jour les stats du plan
        SimpleReadingPlanModel.update_stats(data["plan_id"], "subscribe")
        
        return {
            "message": "Inscription au plan réussie",
            "user_plan_id": str(result.inserted_id)
        }, 201
    
    @staticmethod
    def get_user_plans(user_id, status=None):
        """Récupérer les plans d'un utilisateur"""
        query = {"user_id": ObjectId(user_id)}
        if status:
            query["status"] = status
        
        user_plans = list(UserSimplePlanModel.get_collection().find(query).sort("created_at", -1))
        
        # Enrichir avec les détails du plan
        for user_plan in user_plans:
            user_plan["_id"] = str(user_plan["_id"])
            user_plan["user_id"] = str(user_plan["user_id"])
            user_plan["plan_id"] = str(user_plan["plan_id"])
            
            # Ajouter les détails du plan
            plan = SimpleReadingPlanModel.get_plan_by_id(user_plan["plan_id"])
            if plan:
                user_plan["plan_details"] = {
                    "title": plan["title"],
                    "subtitle": plan["subtitle"],
                    "emoji": plan["meta"]["emoji"],
                    "color": plan["meta"]["color"]
                }
        
        return user_plans
    
    @staticmethod
    def mark_day_completed(user_plan_id, day):
        """Marquer un jour comme complété"""
        user_plan = UserSimplePlanModel.get_collection().find_one({"_id": ObjectId(user_plan_id)})
        if not user_plan:
            return {"message": "Plan utilisateur non trouvé"}, 404
        
        if day not in user_plan["progress"]["completed_days"]:
            # Ajouter le jour aux jours complétés
            UserSimplePlanModel.get_collection().update_one(
                {"_id": ObjectId(user_plan_id)},
                {
                    "$addToSet": {"progress.completed_days": day},
                    "$set": {
                        "progress.last_reading": datetime.utcnow(),
                        "progress.current_day": day + 1
                    }
                }
            )
            
            # Récupérer le plan pour calculer le pourcentage
            plan = SimpleReadingPlanModel.get_plan_by_id(user_plan["plan_id"])
            if plan:
                total_days = len(plan["content"]["reading_schedule"])
                completed_days = len(user_plan["progress"]["completed_days"]) + 1
                completion_percentage = (completed_days / total_days) * 100
                
                # Mettre à jour le pourcentage
                UserSimplePlanModel.get_collection().update_one(
                    {"_id": ObjectId(user_plan_id)},
                    {"$set": {"progress.completion_percentage": completion_percentage}}
                )
                
                # Si 100% complété, marquer comme terminé
                if completion_percentage >= 100:
                    UserSimplePlanModel.get_collection().update_one(
                        {"_id": ObjectId(user_plan_id)},
                        {"$set": {"status": "completed"}}
                    )
                    SimpleReadingPlanModel.update_stats(user_plan["plan_id"], "complete")
        
        return {"message": "Jour marqué comme complété", "current_day": day + 1}, 200
    
    @staticmethod
    def get_current_reading(user_plan_id):
        """Récupérer la lecture actuelle de l'utilisateur"""
        user_plan = UserSimplePlanModel.get_collection().find_one({"_id": ObjectId(user_plan_id)})
        if not user_plan:
            return {"message": "Plan utilisateur non trouvé"}, 404
        
        current_day = user_plan["progress"]["current_day"]
        
        # Récupérer le plan pour obtenir la lecture du jour
        plan = SimpleReadingPlanModel.get_plan_by_id(user_plan["plan_id"])
        if not plan:
            return {"message": "Plan non trouvé"}, 404
        
        # Trouver la lecture du jour actuel
        current_reading = None
        for reading in plan["content"]["reading_schedule"]:
            if reading["day"] == current_day:
                current_reading = reading
                break
        
        if not current_reading:
            return {"message": "Lecture du jour non trouvée"}, 404
        
        return {
            "current_reading": current_reading,
            "progress": user_plan["progress"],
            "plan_title": plan["title"]
        }