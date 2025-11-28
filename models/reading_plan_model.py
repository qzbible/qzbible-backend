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
    def create_plan(data, created_by=None):
        """Créer un plan de lecture simple"""

        # Calculer la date de fin basée sur start_date + duration_months
        start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        
        # Ajouter les mois à la date de début
        end_date = start_date.replace(
            year=start_date.year + (start_date.month + data["duration_months"] - 1) // 12,
            month=(start_date.month + data["duration_months"] - 1) % 12 + 1
        )
        
        plan = {
        "title": data["title"],
        # "subtitle": data["subtitle"],
        "description": data["description"],
        "settings": {
            "start_date": start_date,
            "end_date": end_date,
            "duration_months": data["duration_months"],
            # "daily_chapters": data["daily_chapters"],
            "has_notifications": data.get("has_notifications", True),
            "auto_save_progress": data.get("auto_save_progress", True),
            
            # ✅ Configuration des notifications
            "notification_settings": {
                "enabled": data.get("notification_settings", {}).get("enabled", True),
                "default_time": data.get("notification_settings", {}).get("default_time", "07:00"),
                "frequency": data.get("notification_settings", {}).get("frequency", "daily"),  # daily, weekly, monthly
                "recurrence_pattern": {
                    "type": data.get("notification_settings", {}).get("recurrence_pattern", {}).get("type", "daily"),  # daily, weekly, monthly, yearly
                    "interval": data.get("notification_settings", {}).get("recurrence_pattern", {}).get("interval", 1),  # every X days/weeks/months
                    "days_of_week": data.get("notification_settings", {}).get("recurrence_pattern", {}).get("days_of_week", []),  # [0,1,2,3,4,5,6] pour dim-sam
                    "day_of_month": data.get("notification_settings", {}).get("recurrence_pattern", {}).get("day_of_month", None),  # pour mensuel
                    "end_condition": {
                        "type": data.get("notification_settings", {}).get("recurrence_pattern", {}).get("end_condition", {}).get("type", "never"),  # never, date, count
                        "end_date": data.get("notification_settings", {}).get("recurrence_pattern", {}).get("end_condition", {}).get("end_date", None),
                        "occurrences": data.get("notification_settings", {}).get("recurrence_pattern", {}).get("end_condition", {}).get("occurrences", None)
                    }
                },
                "reminder_types": data.get("notification_settings", {}).get("reminder_types", ["notification"]),  # notification, email, sms
                "advance_reminders": data.get("notification_settings", {}).get("advance_reminders", []),  # ex: [{"minutes": 15}, {"hours": 1}]
                "custom_message": data.get("notification_settings", {}).get("custom_message", None)
            }
        },
        # "content": {
        #     "book_focus": data["book_focus"],
        #     "reading_schedule": data["reading_schedule"]
        # },
        "meta": {
            "emoji": data.get("emoji", "📖"),
            "color": data.get("color", "#2196F3"),
            "created_at": datetime.utcnow(),
            "created_by": ObjectId(created_by) if created_by else None,
            "is_template": data.get("is_template", False),
            "creator_type": "user" if created_by else "system"
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
            "plan_id": str(result.inserted_id),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
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
        """Créer une inscription avec notifications personnalisées"""
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
            
            # ✅ Préférences de notification personnalisées
            "notification_preferences": {
                "enabled": data.get("notification_preferences", {}).get("enabled", True),
                "reminder_time": data.get("notification_preferences", {}).get("reminder_time", "07:00"),
                "frequency": data.get("notification_preferences", {}).get("frequency", "daily"),  # daily, weekly, custom
                "days_of_week": data.get("notification_preferences", {}).get("days_of_week", [1,2,3,4,5,6,0]),  # tous les jours par défaut
                "recurrence": {
                    "type": data.get("notification_preferences", {}).get("recurrence", {}).get("type", "daily"),  # daily, weekly, monthly
                    "interval": data.get("notification_preferences", {}).get("recurrence", {}).get("interval", 1),
                    "custom_pattern": data.get("notification_preferences", {}).get("recurrence", {}).get("custom_pattern", None)
                },
                "advance_reminders": data.get("notification_preferences", {}).get("advance_reminders", []),
                "reminder_types": data.get("notification_preferences", {}).get("reminder_types", ["push"]),  # push, email, sms
                "custom_message": data.get("notification_preferences", {}).get("custom_message", None),
                "snooze_options": data.get("notification_preferences", {}).get("snooze_options", [5, 15, 30, 60]),  # minutes
                "quiet_hours": {
                    "enabled": data.get("notification_preferences", {}).get("quiet_hours", {}).get("enabled", False),
                    "start_time": data.get("notification_preferences", {}).get("quiet_hours", {}).get("start_time", "22:00"),
                    "end_time": data.get("notification_preferences", {}).get("quiet_hours", {}).get("end_time", "06:00")
                }
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