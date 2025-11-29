# services/simple_reading_plan_service.py

from datetime import datetime, timezone, timedelta
from bson import ObjectId

from models.reading_plan_model import SimpleReadingPlanModel, UserSimplePlanModel
 

def create_simple_plan_service(plan_data, created_by=None):
    """Créer un plan de lecture simple"""
    try:
        result = SimpleReadingPlanModel.create_plan(plan_data, created_by)
        return result, 201
    except Exception as e:
        return {"message": f"Erreur lors de la création : {str(e)}"}, 500

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

def generate_plan_days(start_date, end_date):
    """Générer tous les jours du plan de lecture"""
    from datetime import datetime, date, timedelta
    
    # Convertir en objets date si nécessaire
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    days = []
    current_date = start_date
    day_number = 1
    
    while current_date <= end_date:
        days.append({
            "day": day_number,
            "date": current_date.isoformat(),
            "date_formatted": current_date.strftime("%d/%m/%Y"),
            "weekday": current_date.strftime("%A"),
            "weekday_fr": get_french_weekday(current_date.weekday()),
            "is_today": current_date == date.today(),
            "is_past": current_date < date.today(),
            "is_future": current_date > date.today()
        })
        
        current_date += timedelta(days=1)
        day_number += 1
    
    return days

def get_french_weekday(weekday_num):
    """Convertir le numéro de jour en nom français"""
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    return days[weekday_num]

def get_plan_status(progression):
    """Déterminer le statut du plan pour le filtrage"""
    if not progression["is_started"]:
        return "pending"
    elif progression["is_completed"]:
        return "completed"
    else:
        return "active"

def get_user_simple_plans_service(user_id, status_filter=None):
    """
    Récupérer les plans créés par l'utilisateur avec gestion des anciens formats
    """
    from datetime import datetime, date
    from models.reading_plan_model import SimpleReadingPlanModel
    
    try:
        # Récupérer tous les plans créés par l'utilisateur
        plan_filters = {"meta.created_by": ObjectId(user_id)}
        plans = SimpleReadingPlanModel.get_all_plans(plan_filters, 0, 100)
        
        result = []
        current_date = date.today()
        
        for plan in plans:
            try:
                # Calcul de la progression automatique avec gestion d'erreurs
                progression = calculate_plan_progression(plan, current_date)
                
                # Générer les jours après avoir calculé les dates
                plan_days = generate_plan_days(
                    progression["start_date"], 
                    progression["end_date"]
                )
                
                # Filtrer par statut si demandé
                if status_filter:
                    plan_status = get_plan_status(progression)
                    if plan_status != status_filter:
                        continue
                
                # ✅ Gérer les champs manquants
                settings = plan.get("settings", {})
                meta = plan.get("meta", {})
                
                plan_item = {
                    "_id": str(plan["_id"]),
                    "title": plan.get("title", "Plan sans titre"),
                    "description": plan.get("description", "Aucune description"),
                    "emoji": meta.get("emoji", "📖"),
                    "color": meta.get("color", "#2196F3"),
                    "start_date": progression["start_date"],
                    "end_date": progression["end_date"],
                    "duration_months": settings.get("duration_months", 1),
                    "has_notifications": settings.get("has_notifications", True),
                    "created_at": meta.get("created_at", datetime.utcnow()),
                    "days": plan_days,
                    "progression": progression
                }
                
                result.append(plan_item)
                
            except Exception as e:
                print(f"Erreur lors du traitement du plan {plan.get('_id')}: {str(e)}")
                continue  # Ignorer ce plan et continuer avec les autres
        
        # Trier par date de création (plus récent en premier)
        result.sort(key=lambda x: x["created_at"], reverse=True)
        
        return result
        
    except Exception as e:
        print(f"Erreur dans get_user_simple_plans_service: {str(e)}")
        return []
def calculate_plan_progression(plan, current_date, plan_days=None):
    """
    Calcul automatique de progression avec compatibilité anciens plans
    """
    from datetime import datetime, date, timedelta
    
    # ✅ Vérifier si c'est un ancien plan ou nouveau plan
    settings = plan.get("settings", {})
    
    # Nouveau format avec start_date/end_date
    if "start_date" in settings and "end_date" in settings:
        start_date_str = settings["start_date"]
        end_date_str = settings["end_date"]
        
        # Convertir en objets date
        if isinstance(start_date_str, str):
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        else:
            start_date = start_date_str
            
        if isinstance(end_date_str, str):
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            end_date = end_date_str
    
    # Ancien format - calculer à partir de created_at + duration_months
    else:
        duration_months = settings.get("duration_months", 1)
        created_at = plan.get("meta", {}).get("created_at")
        
        if created_at:
            # Utiliser created_at comme start_date
            if hasattr(created_at, 'date'):
                start_date = created_at.date()
            else:
                start_date = datetime.strptime(str(created_at)[:10], "%Y-%m-%d").date()
            
            # Calculer end_date
            end_date = start_date.replace(
                year=start_date.year + (start_date.month + duration_months - 1) // 12,
                month=(start_date.month + duration_months - 1) % 12 + 1
            )
        else:
            # Fallback - utiliser la date actuelle
            start_date = current_date
            end_date = current_date + timedelta(days=30 * duration_months)
    
    # Générer les jours si pas fournis
    if plan_days is None:
        plan_days = generate_plan_days(start_date, end_date)
    
    # Calculs temporels
    total_days = len(plan_days)
    
    # Déterminer le jour actuel dans le plan
    current_day = None
    for day in plan_days:
        if day["is_today"]:
            current_day = day["day"]
            break
    
    # Déterminer le statut selon la date actuelle
    if current_date < start_date:
        elapsed_days = 0
        remaining_days = total_days
        completion_percentage = 0.0
        is_started = False
        is_completed = False
        status_label = f"Commence le {start_date.strftime('%d/%m/%Y')}"
        status_color = "#9E9E9E"
        
    elif current_date > end_date:
        elapsed_days = total_days
        remaining_days = 0
        completion_percentage = 100.0
        is_started = True
        is_completed = True
        status_label = f"Terminé le {end_date.strftime('%d/%m/%Y')}"
        status_color = "#4CAF50"
        
    else:
        elapsed_days = (current_date - start_date).days + 1
        remaining_days = max(0, total_days - elapsed_days)
        completion_percentage = round((elapsed_days / total_days) * 100, 1) if total_days > 0 else 0
        is_started = True
        is_completed = False
        status_label = f"Jour {elapsed_days}/{total_days}"
        status_color = "#2196F3"
    
    return {
        "total_days": total_days,
        "elapsed_days": elapsed_days,
        "remaining_days": remaining_days,
        "completion_percentage": completion_percentage,
        "current_date": current_date.isoformat(),
        "current_day": current_day,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "is_started": is_started,
        "is_completed": is_completed,
        "status_label": status_label,
        "status_color": status_color,
        "days_until_start": max(0, (start_date - current_date).days) if current_date < start_date else 0,
        "days_since_end": max(0, (current_date - end_date).days) if current_date > end_date else 0
    }

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