# services/simple_reading_plan_service.py

from bson import ObjectId

from models.reading_plan_model import SimpleReadingPlanModel, UserSimplePlanModel
 

def create_simple_plan_service(plan_data, created_by=None):
    """Créer un plan de lecture simple"""
    result = SimpleReadingPlanModel.create_plan(plan_data, created_by)
    return result, 201

def get_simple_plans_service(filters=None, page=1, per_page=20):
    """Récupérer les plans simples avec pagination"""
    skip = (page - 1) * per_page
    
    plans = SimpleReadingPlanModel.get_all_plans(filters, skip, per_page)
    total = SimpleReadingPlanModel.count_plans(filters)
    
    # Convertir les ObjectId
    for plan in plans:
        plan["_id"] = str(plan["_id"])
    
    return {
        "data": plans,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

def get_simple_plan_detail_service(plan_id):
    """Récupérer les détails d'un plan simple"""
    plan = SimpleReadingPlanModel.get_plan_by_id(plan_id)
    
    if not plan:
        return {"message": "Plan non trouvé"}, 404
    
    # Formater pour l'interface
    response = {
        "title": plan["title"],
        "subtitle": plan["subtitle"],
        "description": plan["description"],
        "duration": {
            "months": plan["settings"]["duration_months"],
            "label": f"{plan['settings']['duration_months']} mois"
        },
        "daily_reading": {
            "chapters": plan["settings"]["daily_chapters"],
            "label": f"{plan['settings']['daily_chapters']} chapitres par jour"
        },
        "notifications": {
            "available": plan["settings"]["has_notifications"],
            "label": "Notifications quotidiennes disponibles"
        },
        "auto_save": {
            "enabled": plan["settings"]["auto_save_progress"],
            "label": "Progression automatiquement sauvegardée"
        },
        "schedule_preview": plan["content"]["reading_schedule"][:3],  # 3 premiers jours
        "meta": {
            "emoji": plan["meta"]["emoji"],
            "color": plan["meta"]["color"]
        },
        "stats": plan["stats"]
    }
    
    return response

def subscribe_to_simple_plan_service(plan_id, user_id, subscription_data):
    """S'inscrire à un plan simple"""
    data = {
        "plan_id": plan_id,
        "user_id": user_id,
        "reminder_time": subscription_data.get("reminder_time", "07:00"),
        "reminder_enabled": subscription_data.get("reminder_enabled", True)
    }
    
    result, status = UserSimplePlanModel.create_subscription(data)
    return result, status


def get_user_simple_plans_service(user_id, status=None, filter_type="all"):
    """
    Récupérer les plans simples d'un utilisateur
    filter_type: 'created', 'subscribed', 'all'
    """
    result = []
    
    if filter_type in ["created", "all"]:
        # 1. Plans créés par l'utilisateur
        from models.reading_plan_model import SimpleReadingPlanModel
        
        plan_filters = {"meta.created_by": ObjectId(user_id)}
        created_plans = SimpleReadingPlanModel.get_all_plans(plan_filters, 0, 100)
        
        for plan in created_plans:
            # Récupérer l'inscription
            user_subscription = UserSimplePlanModel.get_collection().find_one({
                "user_id": ObjectId(user_id),
                "plan_id": ObjectId(plan["_id"])
            })
            
            if user_subscription and (not status or user_subscription.get("status") == status):
                plan_item = {
                    "_id": str(user_subscription["_id"]),
                    "user_id": str(user_subscription["user_id"]),
                    "plan_id": str(user_subscription["plan_id"]),
                    "progress": user_subscription["progress"],
                    "notification_preferences": user_subscription.get('notification_preferences', None),
                    "status": user_subscription["status"],
                    "created_at": user_subscription["created_at"],
                    "plan_details": {
                        "title": plan["title"],
                        "subtitle": plan["subtitle"],
                        "emoji": plan["meta"]["emoji"],
                        "color": plan["meta"]["color"],
                        "is_owner": True
                    }
                }
                result.append(plan_item)
    
    if filter_type in ["subscribed", "all"]:
        # 2. Plans auxquels l'utilisateur est inscrit (mais qu'il n'a pas créés)
        subscriptions = UserSimplePlanModel.get_user_plans(user_id, status)
        
        for subscription in subscriptions:
            # Vérifier si ce n'est pas un plan qu'il a créé (pour éviter les doublons)
            plan_id = subscription["plan_id"]
            from models.reading_plan_model import SimpleReadingPlanModel
            plan = SimpleReadingPlanModel.get_plan_by_id(plan_id)
            
            if plan and str(plan.get("meta", {}).get("created_by", "")) != user_id:
                subscription["plan_details"]["is_owner"] = False
                result.append(subscription)
    
    return result

def mark_day_completed_service(user_plan_id, day):
    """Marquer un jour comme complété"""
    result, status = UserSimplePlanModel.mark_day_completed(user_plan_id, day)
    return result, status

def get_current_reading_service(user_plan_id):
    """Récupérer la lecture actuelle"""
    try:
        print(f"DEBUG: Recherche user_plan_id = {user_plan_id}")
        
        user_plan = UserSimplePlanModel.get_collection().find_one({"_id": ObjectId(user_plan_id)})
        
        if not user_plan:
            print(f"DEBUG: Aucun user_plan trouvé avec l'ID {user_plan_id}")
            return {"message": "Plan utilisateur non trouvé"}, 404
        
        print(f"DEBUG: User plan trouvé: {user_plan}")
        
        current_day = user_plan["progress"]["current_day"]
        print(f"DEBUG: Current day = {current_day}")
        
        # Récupérer le plan pour obtenir la lecture du jour
        plan = SimpleReadingPlanModel.get_plan_by_id(user_plan["plan_id"])
        if not plan:
            print(f"DEBUG: Plan principal non trouvé avec l'ID {user_plan['plan_id']}")
            return {"message": "Plan non trouvé"}, 404
        
        print(f"DEBUG: Plan principal trouvé: {plan['title']}")
        
        # Trouver la lecture du jour actuel
        current_reading = None
        for reading in plan["content"]["reading_schedule"]:
            if reading["day"] == current_day:
                current_reading = reading
                break
        
        if not current_reading:
            print(f"DEBUG: Aucune lecture trouvée pour le jour {current_day}")
            return {"message": "Lecture du jour non trouvée"}, 404
        
        print(f"DEBUG: Lecture trouvée: {current_reading}")
        
        return {
            "current_reading": current_reading,
            "progress": user_plan["progress"],
            "plan_title": plan["title"]
        }
        
    except Exception as e:
        print(f"DEBUG: Exception = {str(e)}")
        return {"message": f"Erreur : {str(e)}"}, 500

def search_simple_plans_service(search_term):
    """Rechercher dans les plans simples"""
    filters = {"search": search_term}
    plans = SimpleReadingPlanModel.get_all_plans(filters, 0, 20)
    
    for plan in plans:
        plan["_id"] = str(plan["_id"])
    
    return plans