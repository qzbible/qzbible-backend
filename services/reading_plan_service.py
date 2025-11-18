# services/simple_reading_plan_service.py

from bson import ObjectId

from models.reading_plan_model import SimpleReadingPlanModel, UserSimplePlanModel
 

def create_simple_plan_service(plan_data):
    """Créer un plan de lecture simple"""
    result = SimpleReadingPlanModel.create_plan(plan_data)
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

def get_user_simple_plans_service(user_id, status=None):
    """Récupérer les plans simples d'un utilisateur"""
    return UserSimplePlanModel.get_user_plans(user_id, status)

def mark_day_completed_service(user_plan_id, day):
    """Marquer un jour comme complété"""
    result, status = UserSimplePlanModel.mark_day_completed(user_plan_id, day)
    return result, status

def get_current_reading_service(user_plan_id):
    """Récupérer la lecture actuelle"""
    result = UserSimplePlanModel.get_current_reading(user_plan_id)
    if isinstance(result, tuple):
        return result
    return result

def search_simple_plans_service(search_term):
    """Rechercher dans les plans simples"""
    filters = {"search": search_term}
    plans = SimpleReadingPlanModel.get_all_plans(filters, 0, 20)
    
    for plan in plans:
        plan["_id"] = str(plan["_id"])
    
    return plans