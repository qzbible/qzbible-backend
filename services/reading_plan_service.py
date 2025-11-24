# services/simple_reading_plan_service.py

from datetime import datetime, timezone, timedelta
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


def get_user_simple_plans_service(user_id, status=None):
    """Récupérer les plans avec calculs de progression"""
    user_plans = UserSimplePlanModel.get_user_plans(user_id, status)
    
    for user_plan in user_plans:
        # Récupérer le plan principal pour les calculs
        plan = SimpleReadingPlanModel.get_plan_by_id(user_plan["plan_id"])
        
        if plan:
            total_days = len(plan["content"]["reading_schedule"])
            completed_days = len(user_plan["progress"]["completed_days"])
            current_day = user_plan["progress"]["current_day"]
            
            # ✅ Calculs de progression
            progression_stats = {
                "total_days": total_days,
                "completed_days": completed_days,
                "remaining_days": max(0, total_days - completed_days),
                "completion_percentage": round((completed_days / total_days) * 100, 1) if total_days > 0 else 0,
                "current_day": current_day,
                "is_behind": current_day > completed_days + 1,  # En retard ?
                "days_behind": max(0, current_day - completed_days - 1),
                
                # Temps estimé
                "estimated_completion_date": None,
                "days_since_start": None,
                "average_completion_rate": None
            }
            
            # Calcul des dates
            if user_plan["progress"].get("started_at"):
                started_at = user_plan["progress"]["started_at"]
                days_since_start = (datetime.utcnow() - started_at).days + 1
                progression_stats["days_since_start"] = days_since_start
                
                # Taux de completion moyen
                if days_since_start > 0:
                    avg_rate = completed_days / days_since_start
                    progression_stats["average_completion_rate"] = round(avg_rate, 2)
                    
                    # Date estimée de fin (si on continue au même rythme)
                    if avg_rate > 0:
                        remaining_days_needed = (total_days - completed_days) / avg_rate
                        estimated_completion = datetime.utcnow() + timedelta(days=remaining_days_needed)
                        progression_stats["estimated_completion_date"] = estimated_completion.strftime("%Y-%m-%d")
            
            # Statut de progression
            if progression_stats["completion_percentage"] == 100:
                progression_stats["status_label"] = "Terminé"
                progression_stats["status_color"] = "#4CAF50"
            elif progression_stats["is_behind"]:
                progression_stats["status_label"] = f"En retard de {progression_stats['days_behind']} jour(s)"
                progression_stats["status_color"] = "#FF9800"
            elif completed_days >= current_day - 1:
                progression_stats["status_label"] = "À jour"
                progression_stats["status_color"] = "#2196F3"
            else:
                progression_stats["status_label"] = "En avance"
                progression_stats["status_color"] = "#4CAF50"
            
            user_plan["progression"] = progression_stats
    
    return user_plans

# def get_user_simple_plans_service(user_id, status=None, filter_type="all"):
#     """
#     Récupérer les plans simples d'un utilisateur
#     filter_type: 'created', 'subscribed', 'all'
#     """
#     result = []
    
#     if filter_type in ["created", "all"]:
#         # 1. Plans créés par l'utilisateur
#         from models.reading_plan_model import SimpleReadingPlanModel
        
#         plan_filters = {"meta.created_by": ObjectId(user_id)}
#         created_plans = SimpleReadingPlanModel.get_all_plans(plan_filters, 0, 100)
        
#         for plan in created_plans:
#             # Récupérer l'inscription
#             user_subscription = UserSimplePlanModel.get_collection().find_one({
#                 "user_id": ObjectId(user_id),
#                 "plan_id": ObjectId(plan["_id"])
#             })
            
#             if user_subscription and (not status or user_subscription.get("status") == status):
#                 plan_item = {
#                     "_id": str(user_subscription["_id"]),
#                     "user_id": str(user_subscription["user_id"]),
#                     "plan_id": str(user_subscription["plan_id"]),
#                     "progress": user_subscription["progress"],
#                     "notification_preferences": user_subscription.get('notification_preferences', None),
#                     "status": user_subscription["status"],
#                     "created_at": user_subscription["created_at"],
#                     "plan_details": {
#                         "title": plan["title"],
#                         "subtitle": plan["subtitle"],
#                         "emoji": plan["meta"]["emoji"],
#                         "color": plan["meta"]["color"],
#                         "is_owner": True
#                     }
#                 }
#                 result.append(plan_item)
    
#     if filter_type in ["subscribed", "all"]:
#         # 2. Plans auxquels l'utilisateur est inscrit (mais qu'il n'a pas créés)
#         subscriptions = UserSimplePlanModel.get_user_plans(user_id, status)
        
#         for subscription in subscriptions:
#             # Vérifier si ce n'est pas un plan qu'il a créé (pour éviter les doublons)
#             plan_id = subscription["plan_id"]
#             from models.reading_plan_model import SimpleReadingPlanModel
#             plan = SimpleReadingPlanModel.get_plan_by_id(plan_id)
            
#             if plan and str(plan.get("meta", {}).get("created_by", "")) != user_id:
#                 subscription["plan_details"]["is_owner"] = False
#                 result.append(subscription)
    
#     return result


def get_user_simple_plans_service(user_id, status=None, filter_type="all"):
    """
    Récupérer les plans simples d'un utilisateur avec calculs de progression
    filter_type: 'created', 'subscribed', 'all'
    """
    from datetime import datetime, timezone, timedelta
    result = []
    
    if filter_type in ["created", "all"]:
        # 1. Plans créés par l'utilisateur
        from models.reading_plan_model import SimpleReadingPlanModel  # ✅ Correction : bon import
        
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
                    "notification_preferences": user_subscription.get('notification_preferences', {}),  # ✅ Correction : dict par défaut
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
                
                # ✅ Ajouter les calculs de progression
                plan_item = add_progression_calculations(plan_item, plan)
                result.append(plan_item)
    
    if filter_type in ["subscribed", "all"]:
        # 2. Plans auxquels l'utilisateur est inscrit (mais qu'il n'a pas créés)
        subscriptions = UserSimplePlanModel.get_user_plans(user_id, status)
        
        for subscription in subscriptions:
            # Vérifier si ce n'est pas un plan qu'il a créé (pour éviter les doublons)
            plan_id = subscription["plan_id"]
            from models.reading_plan_model import SimpleReadingPlanModel  # ✅ Correction : bon import
            plan = SimpleReadingPlanModel.get_plan_by_id(plan_id)
            
            if plan and str(plan.get("meta", {}).get("created_by", "")) != user_id:
                subscription["plan_details"]["is_owner"] = False
                
                # ✅ Ajouter les calculs de progression
                subscription = add_progression_calculations(subscription, plan)
                result.append(subscription)
    
    return result

def add_progression_calculations(user_plan, plan):
    """Calcul automatique de progression basé sur la date système et la configuration"""
    from datetime import datetime, timezone, timedelta
    
    if not plan or not plan.get("content", {}).get("reading_schedule"):
        return user_plan
    
    total_days = len(plan["content"]["reading_schedule"])
    completed_days = len(user_plan["progress"].get("completed_days", []))
    
    # ✅ Calcul automatique du jour attendu selon la date système
    if user_plan["progress"].get("started_at"):
        started_at = user_plan["progress"]["started_at"]
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        days_since_start = (now - started_at).days + 1
        
        # Le jour où l'utilisateur DEVRAIT être selon la configuration
        expected_current_day = min(days_since_start, total_days)
        
        # Gestion de la fréquence (si c'est pas quotidien)
        frequency = user_plan.get("notification_preferences", {}).get("frequency", "daily")
        days_of_week = user_plan.get("notification_preferences", {}).get("days_of_week", [0,1,2,3,4,5,6])
        
        if frequency == "weekly" or len(days_of_week) < 7:
            # Calculer combien de jours "actifs" se sont écoulés
            expected_current_day = calculate_active_days(started_at, now, days_of_week)
    else:
        expected_current_day = 1
        days_since_start = 1
    
    # Calculs de progression basés sur la réalité
    progression_stats = {
        "total_days": total_days,
        "completed_days": completed_days,
        "remaining_days": max(0, total_days - completed_days),
        "completion_percentage": round((completed_days / total_days) * 100, 1) if total_days > 0 else 0,
        
        # ✅ Jour attendu calculé automatiquement
        "expected_current_day": expected_current_day,
        "days_since_start": days_since_start,
        
        # ✅ Nouveau calcul du retard basé sur l'attendu vs réalisé
        "is_behind": completed_days < expected_current_day,
        "days_behind": max(0, expected_current_day - completed_days),
        "days_ahead": max(0, completed_days - expected_current_day),
        
        # Prédictions
        "average_completion_rate": None,
        "estimated_completion_date": None
    }
    
    # Taux de completion réel
    if days_since_start > 0:
        avg_rate = completed_days / days_since_start
        progression_stats["average_completion_rate"] = round(avg_rate, 2)
        
        # Date estimée selon le rythme actuel
        if avg_rate > 0:
            remaining_days_needed = (total_days - completed_days) / avg_rate
            estimated_completion = now + timedelta(days=remaining_days_needed)
            progression_stats["estimated_completion_date"] = estimated_completion.strftime("%Y-%m-%d")
    
    # ✅ Statut intelligent basé sur la progression réelle
    if progression_stats["completion_percentage"] == 100:
        progression_stats["status_label"] = "Terminé"
        progression_stats["status_color"] = "#4CAF50"
    elif progression_stats["is_behind"]:
        days_behind = progression_stats["days_behind"]
        progression_stats["status_label"] = f"En retard de {days_behind} jour(s)"
        progression_stats["status_color"] = "#FF9800"
    elif progression_stats["days_ahead"] > 0:
        days_ahead = progression_stats["days_ahead"]
        progression_stats["status_label"] = f"En avance de {days_ahead} jour(s)"
        progression_stats["status_color"] = "#4CAF50"
    else:
        progression_stats["status_label"] = "À jour"
        progression_stats["status_color"] = "#2196F3"
    
    user_plan["progression"] = progression_stats
    return user_plan

def calculate_active_days(started_at, current_date, days_of_week):
    """Calculer le nombre de jours actifs selon la configuration"""
    if len(days_of_week) == 7:  # Tous les jours
        return (current_date - started_at).days + 1
    
    # Compter seulement les jours configurés
    active_days = 0
    current = started_at.date()
    end_date = current_date.date()
    
    while current <= end_date:
        if current.weekday() in [(d-1) % 7 for d in days_of_week]:  # Conversion dim=0 vers lun=0
            active_days += 1
        current += timedelta(days=1)
    
    return active_days

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