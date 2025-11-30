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

 

def generate_relevant_plan_days(start_date, end_date, current_date, plan_status="active"):
    """
    Générer les jours pertinents selon le statut du plan
    - Plan futur: 5 premiers jours
    - Plan actif: 2 passés + aujourd'hui + 2 futurs  
    - Plan terminé: 5 derniers jours
    """
    from datetime import datetime, date, timedelta
    
    # Convertir en objets date si nécessaire
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    if isinstance(current_date, str):
        current_date = datetime.strptime(current_date, "%Y-%m-%d").date()
    
    days = []
    
    if plan_status == "pending":  # Plan pas encore commencé
        # ✅ Afficher les 5 premiers jours du plan
        current_loop_date = start_date
        day_number = 1
        count = 0
        
        while current_loop_date <= end_date and count < 5:
            days.append(create_day_object(current_loop_date, day_number, current_date, start_date, end_date))
            current_loop_date += timedelta(days=1)
            day_number += 1
            count += 1
            
    elif plan_status == "completed":  # Plan terminé
        # ✅ Afficher les 5 derniers jours du plan
        total_days = (end_date - start_date).days + 1
        last_5_start = max(1, total_days - 4)  # Commencer 4 jours avant la fin
        
        current_loop_date = start_date + timedelta(days=last_5_start - 1)
        day_number = last_5_start
        
        while current_loop_date <= end_date:
            days.append(create_day_object(current_loop_date, day_number, current_date, start_date, end_date))
            current_loop_date += timedelta(days=1)
            day_number += 1
            
    else:  # Plan actif
        # ✅ 2 passés + aujourd'hui + 2 futurs
        range_start = max(start_date, current_date - timedelta(days=2))
        range_end = min(end_date, current_date + timedelta(days=2))
        
        start_day_number = (range_start - start_date).days + 1
        current_loop_date = range_start
        day_number = start_day_number
        
        while current_loop_date <= range_end:
            if start_date <= current_loop_date <= end_date:
                days.append(create_day_object(current_loop_date, day_number, current_date, start_date, end_date))
            current_loop_date += timedelta(days=1)
            day_number += 1
    
    return days


def create_day_object(day_date, day_number, current_date, start_date, end_date):
    """Créer un objet jour standardisé"""
    return {
        "day": day_number,
        "date": day_date.isoformat(),
        "date_formatted": day_date.strftime("%d/%m/%Y"),
        "weekday": day_date.strftime("%A"),
        "weekday_fr": get_french_weekday(day_date.weekday()),
        "is_today": day_date == current_date,
        "is_past": day_date < current_date,
        "is_future": day_date > current_date,
        "is_in_plan": start_date <= day_date <= end_date
    }

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
    Récupérer TOUS les plans avec des jours optimisés selon leur statut
    """
    from datetime import datetime, date
    from models.reading_plan_model import SimpleReadingPlanModel
    
    try:
        plan_filters = {"meta.created_by": ObjectId(user_id)}
        plans = SimpleReadingPlanModel.get_all_plans(plan_filters, 0, 100)
        
        result = []
        current_date = date.today()
        
        for plan in plans:
            try:
                progression = calculate_plan_progression_with_recurrence(plan, current_date)
            
                # Générer les jours avec statut de pause
                relevant_days = generate_relevant_plan_days_with_pauses(
                    progression["start_date"], 
                    progression["end_date"],
                    current_date,
                    plan,  # ✅ Passer le plan complet
                    plan_status=progression["plan_status"]
                ) 
                # ✅ Filtrer par statut SEULEMENT si demandé
                if status_filter:
                    if progression["plan_status"] != status_filter:
                        continue
                
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
                    "relevant_days": relevant_days,
                    "progression": progression,
                    "current_status": plan.get("current_status", "active"),
                    "is_paused": plan.get("current_status") == "paused",
                    "pause_info": get_current_pause_info(plan),
                    "notification_settings": settings.get("notification_settings", {}),
                }
                
                result.append(plan_item)
                
            except Exception as e:
                print(f"Erreur lors du traitement du plan {plan.get('_id')}: {str(e)}")
                continue
        
        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result
        
    except Exception as e:
        print(f"Erreur dans get_user_simple_plans_service: {str(e)}")
        return []

def get_current_pause_info(plan):
    """Récupérer les infos de la pause actuelle"""
    if plan.get("current_status") != "paused":
        return None
    
    pause_history = plan.get("pause_history", [])
    for pause in reversed(pause_history):
        if pause.get("resume_date") is None:
            return {
                "pause_date": pause["pause_date"],
                "reason": pause.get("reason", ""),
                "paused_days": (datetime.now().date() - 
                              datetime.strptime(pause["pause_date"], "%Y-%m-%d").date()).days
            }
    return None   

 

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

 
def get_simple_plan_details_service(plan_id, user_id, include_all_days=False):
    """
    Récupérer les détails complets d'un plan de lecture
    """
    from datetime import datetime, date
    from models.reading_plan_model import SimpleReadingPlanModel
    from bson import ObjectId
    from bson.errors import InvalidId
    
    try:
        # Valider l'ObjectId
        if not ObjectId.is_valid(plan_id):
            raise ValueError("ID de plan invalide")
        
        # Récupérer le plan
        plan = SimpleReadingPlanModel.get_plan_by_id(plan_id)
        
        if not plan:
            return None
        # Vérifier les droits d'accès
        # Pour l'instant, seul le créateur peut voir le plan
        # Vous pouvez ajouter d'autres logiques d'accès ici
        plan_creator = plan.get("meta", {}).get("created_by")
        is_owner = str(plan_creator) == user_id if plan_creator else False
        
        if not is_owner:
            # Vous pouvez ajouter ici la logique pour les plans publics
            # ou les souscriptions
            return None
        
        current_date = date.today()
        
        # Calcul de la progression
        progression = calculate_plan_progression_with_recurrence(plan, current_date)
        
        # Générer les jours selon le paramètre
        if include_all_days:
            # Tous les jours du plan
            plan_days = generate_all_plan_days(
                progression["start_date"],
                progression["end_date"]
            )
        else:
            # Seulement les 5 jours pertinents
            plan_days = generate_relevant_plan_days_with_pauses(
                    progression["start_date"], 
                    progression["end_date"],
                    current_date,
                    plan,  # ✅ Passer le plan complet
                    plan_status=progression["plan_status"]
                )
            # plan_days = generate_relevant_plan_days(
            #     progression["start_date"], 
            #     progression["end_date"],
            #     current_date,
            #     plan_status=progression["plan_status"]
            # )
        
        # Construire la réponse détaillée
        settings = plan.get("settings", {})
        meta = plan.get("meta", {})
        
        plan_details = {
            "_id": str(plan["_id"]),
            "title": plan.get("title", "Plan sans titre"),
            "description": plan.get("description", "Aucune description"),
            "emoji": meta.get("emoji", "📖"),
            "color": meta.get("color", "#2196F3"),
            "start_date": progression["start_date"],
            "end_date": progression["end_date"],
            "duration_months": settings.get("duration_months", 1),
            "has_notifications": settings.get("has_notifications", True),
            "auto_save_progress": settings.get("auto_save_progress", True),
            "is_template": meta.get("is_template", False),
            
            # Paramètres de notification détaillés
            "notification_settings": settings.get("notification_settings", {}),
            
            # Informations de propriété
            "is_owner": is_owner,
            "created_at": meta.get("created_at"),
            "creator_type": meta.get("creator_type", "user"),
            
            # Jours et progression
            "days": plan_days,
            "progression": progression,
            
            # Métadonnées supplémentaires
            "total_days_in_plan": len(plan_days) if include_all_days else progression["total_days"]
        }
        
        return plan_details
        
    except Exception as e:
        print(f"Erreur dans get_simple_plan_details_service: {str(e)}")
        return None
    
def generate_all_plan_days(start_date, end_date):
    """
    Générer TOUS les jours du plan (pour l'option include_all_days=true)
    """
    from datetime import datetime, date, timedelta
    
    # Convertir en objets date si nécessaire
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    days = []
    current_date = date.today()
    current_loop_date = start_date
    day_number = 1
    
    while current_loop_date <= end_date:
        days.append({
            "day": day_number,
            "date": current_loop_date.isoformat(),
            "date_formatted": current_loop_date.strftime("%d/%m/%Y"),
            "weekday": current_loop_date.strftime("%A"),
            "weekday_fr": get_french_weekday(current_loop_date.weekday()),
            "is_today": current_loop_date == current_date,
            "is_past": current_loop_date < current_date,
            "is_future": current_loop_date > current_date,
            "is_in_plan": True
        })
        
        current_loop_date += timedelta(days=1)
        day_number += 1
    
    return days

def generate_relevant_plan_days_with_pauses(start_date, end_date, current_date, plan, plan_status="active"):
    """
    Générer les jours avec gestion des pauses basé sur days_of_week
    """
    from datetime import datetime, date, timedelta
    
    # Convertir les dates
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    if isinstance(current_date, str):
        current_date = datetime.strptime(current_date, "%Y-%m-%d").date()
    
    # ✅ Récupérer la configuration de récurrence
    settings = plan.get("settings", {})
    recurrence_pattern = settings.get("recurrence_pattern", {})
    days_of_week = recurrence_pattern.get("days_of_week", [0,1,2,3,4,5,6])  # Tous les jours par défaut
    
    # Récupérer l'historique des pauses
    pause_history = plan.get("pause_history", [])
    current_plan_status = plan.get("current_status", "active")
    
    # ✅ Calculer tous les jours actifs du plan selon days_of_week
    all_active_days = calculate_active_days_by_weekdays(start_date, end_date, days_of_week)
    
    # ✅ Filtrer les jours selon le statut pour retourner seulement 5 jours pertinents
    relevant_active_days = []
    
    if plan_status == "pending":
        # 5 premiers jours actifs
        relevant_active_days = all_active_days[:5]
        
    elif plan_status == "completed":
        # 5 derniers jours actifs
        relevant_active_days = all_active_days[-5:] if len(all_active_days) > 5 else all_active_days
        
    else:  # active ou paused
        # Trouver le jour actif actuel et prendre 2 avant + aujourd'hui + 2 après
        current_active_day_index = None
        
        for i, active_day in enumerate(all_active_days):
            if active_day["date"] <= current_date:
                current_active_day_index = i
        
        if current_active_day_index is not None:
            start_index = max(0, current_active_day_index - 2)
            end_index = min(len(all_active_days), current_active_day_index + 3)
            relevant_active_days = all_active_days[start_index:end_index]
        else:
            # Si aucun jour actif trouvé, prendre les 5 premiers
            relevant_active_days = all_active_days[:5]
    
    # ✅ Enrichir chaque jour avec les infos de pause et statut
    days = []
    for active_day in relevant_active_days:
        day_date = active_day["date"]
        
        # Vérifier si ce jour est dans une période de pause
        is_paused = is_date_in_pause_period(day_date, pause_history)
        
        # Déterminer le statut du jour
        if is_paused:
            day_status = "paused"
        elif day_date < current_date:
            day_status = "completed"
        elif day_date == current_date:
            day_status = "current"
        else:
            day_status = "pending"
        
        day_obj = {
            "day": active_day["day_number"],
            "date": day_date.isoformat(),
            "date_formatted": day_date.strftime("%d/%m/%Y"),
            "weekday": day_date.strftime("%A"),
            "weekday_fr": active_day["weekday_name"],
            "is_today": day_date == current_date,
            "is_past": day_date < current_date,
            "is_future": day_date > current_date,
            "is_in_plan": True,
            "is_active_day": True,  # ✅ Tous ces jours sont actifs selon la récurrence
            "is_paused": is_paused,
            "status": day_status
        }
        
        days.append(day_obj)
    
    return days

def is_date_in_pause_period(check_date, pause_history):
    """Vérifier si une date est dans une période de pause"""
    from datetime import datetime, date
    
    for pause in pause_history:
        pause_start = datetime.strptime(pause["pause_date"], "%Y-%m-%d").date()
        
        if pause["resume_date"]:
            pause_end = datetime.strptime(pause["resume_date"], "%Y-%m-%d").date()
        else:
            # Pause active - considérer jusqu'à aujourd'hui
            pause_end = date.today()
        
        if pause_start <= check_date <= pause_end:
            return True
    
    return False

def is_date_in_pause_period(check_date, pause_history):
    """Vérifier si une date est dans une période de pause"""
    from datetime import datetime
    
    for pause in pause_history:
        pause_start = datetime.strptime(pause["pause_date"], "%Y-%m-%d").date()
        pause_end = None
        
        if pause["resume_date"]:
            pause_end = datetime.strptime(pause["resume_date"], "%Y-%m-%d").date()
        else:
            # Pause active - considérer jusqu'à aujourd'hui
            pause_end = datetime.now().date()
        
        if pause_start <= check_date <= pause_end:
            return True
    
    return False

def pause_plan_service(plan_id, user_id, data):
    """Mettre un plan en pause"""
    from datetime import datetime, date
    from models.reading_plan_model import SimpleReadingPlanModel
    
    plan = SimpleReadingPlanModel.get_plan_by_id(plan_id)
    if not plan:
        raise ValueError("Plan non trouvé")
    
    # Vérifier les droits
    if str(plan.get("meta", {}).get("created_by")) != user_id:
        raise ValueError("Accès non autorisé")
    
    # Vérifier que le plan n'est pas déjà en pause
    if plan.get("current_status") == "paused":
        raise ValueError("Le plan est déjà en pause")
    
    pause_date_str = data.get("pause_date", date.today().isoformat())
    pause_date = datetime.strptime(pause_date_str, "%Y-%m-%d").date()
    
    # Créer l'entrée de pause
    pause_entry = {
        "pause_date": pause_date.isoformat(),
        "resume_date": None,
        "reason": data.get("reason", ""),
        "paused_by": ObjectId(user_id),
        "created_at": datetime.utcnow()
    }
    
    # Mettre à jour le plan
    update_data = {
        "$set": {
            "current_status": "paused"
        },
        "$push": {
            "pause_history": pause_entry
        }
    }
    
    SimpleReadingPlanModel.get_collection().update_one(
        {"_id": ObjectId(plan_id)},
        update_data
    )
    
    return {
        "message": "Plan mis en pause avec succès",
        "pause_date": pause_date.isoformat(),
        "status": "paused"
    }

def resume_plan_service(plan_id, user_id, data):
    """Reprendre un plan en pause"""
    from datetime import datetime, date
    from models.reading_plan_model import SimpleReadingPlanModel
    
    plan = SimpleReadingPlanModel.get_plan_by_id(plan_id)
    if not plan:
        raise ValueError("Plan non trouvé")
    
    if str(plan.get("meta", {}).get("created_by")) != user_id:
        raise ValueError("Accès non autorisé")
    
    if plan.get("current_status") != "paused":
        raise ValueError("Le plan n'est pas en pause")
    
    resume_date_str = data.get("resume_date", date.today().isoformat())
    resume_date = datetime.strptime(resume_date_str, "%Y-%m-%d").date()
    adjust_schedule = data.get("adjust_schedule", True)
    
    # Trouver la dernière pause
    pause_history = plan.get("pause_history", [])
    last_pause = None
    for pause in reversed(pause_history):
        if pause.get("resume_date") is None:
            last_pause = pause
            break
    
    if not last_pause:
        raise ValueError("Aucune pause active trouvée")
    
    pause_date = datetime.strptime(last_pause["pause_date"], "%Y-%m-%d").date()
    paused_days = (resume_date - pause_date).days
    
    # Calculer le nouvel end_date si ajustement demandé
    new_end_date = None
    if adjust_schedule:
        original_end_date = datetime.strptime(plan["settings"]["end_date"], "%Y-%m-%d").date()
        new_end_date = original_end_date + timedelta(days=paused_days)
    
    # Mettre à jour l'historique de pause
    update_data = {
        "$set": {
            "current_status": "active",
            f"pause_history.{len(pause_history) - 1}.resume_date": resume_date.isoformat()
        }
    }
    
    if new_end_date:
        update_data["$set"]["settings.end_date"] = new_end_date.isoformat()
        update_data["$inc"] = {"pause_adjustments.total_paused_days": paused_days}
    
    SimpleReadingPlanModel.get_collection().update_one(
        {"_id": ObjectId(plan_id)},
        update_data
    )
    
    return {
        "message": "Plan repris avec succès",
        "resume_date": resume_date.isoformat(),
        "paused_days": paused_days,
        "new_end_date": new_end_date.isoformat() if new_end_date else None,
        "status": "active"
    }


def calculate_plan_progression_with_recurrence(plan, current_date):
    """
    Calcul de progression basé uniquement sur les days_of_week configurés
    """
    from datetime import datetime, date, timedelta
    
    # Gestion de la compatibilité avec les anciens plans
    settings = plan.get("settings", {})
    
    if "start_date" in settings and "end_date" in settings:
        start_date_str = settings["start_date"]
        end_date_str = settings["end_date"]
        
        if isinstance(start_date_str, str):
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        else:
            start_date = start_date_str
            
        if isinstance(end_date_str, str):
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            end_date = end_date_str
    else:
        # Ancien format
        duration_months = settings.get("duration_months", 1)
        created_at = plan.get("meta", {}).get("created_at")
        
        if created_at:
            if hasattr(created_at, 'date'):
                start_date = created_at.date()
            else:
                start_date = datetime.strptime(str(created_at)[:10], "%Y-%m-%d").date()
            
            end_date = start_date.replace(
                year=start_date.year + (start_date.month + duration_months - 1) // 12,
                month=(start_date.month + duration_months - 1) % 12 + 1
            )
        else:
            start_date = current_date
            end_date = current_date + timedelta(days=30 * duration_months)
    
    # ✅ Récupérer UNIQUEMENT les days_of_week
    recurrence_pattern = settings.get("recurrence_pattern", {})
    days_of_week = recurrence_pattern.get("days_of_week", [0,1,2,3,4,5,6])  # Tous les jours par défaut
    
    # ✅ Calculer tous les jours actifs selon days_of_week
    active_days = calculate_active_days_by_weekdays(start_date, end_date, days_of_week)
    total_active_days = len(active_days)
    
    # ✅ Calculer les jours actifs écoulés jusqu'à aujourd'hui
    if current_date < start_date:
        elapsed_active_days = 0
        current_active_day = None
    else:
        end_calculation_date = min(current_date, end_date)
        elapsed_active_days_list = calculate_active_days_by_weekdays(start_date, end_calculation_date, days_of_week)
        elapsed_active_days = len(elapsed_active_days_list)
        
        # Trouver le jour actif actuel
        current_active_day = None
        for day in active_days:
            if day["date"] == current_date:
                current_active_day = day["day_number"]
                break
    
    # ✅ Gestion des pauses
    pause_history = plan.get("pause_history", [])
    current_plan_status = plan.get("current_status", "active")
    
    if pause_history:
        paused_active_days = calculate_paused_active_days(pause_history, active_days, current_date)
        effective_elapsed_days = max(0, elapsed_active_days - paused_active_days)
        total_paused_days = paused_active_days
    else:
        effective_elapsed_days = elapsed_active_days
        total_paused_days = 0
    
    # ✅ Déterminer le statut
    if current_plan_status == "paused":
        completion_percentage = round((effective_elapsed_days / total_active_days) * 100, 1) if total_active_days > 0 else 0
        remaining_days = max(0, total_active_days - effective_elapsed_days)
        is_started = effective_elapsed_days > 0
        is_completed = False
        status_label = f"En pause - Jour {effective_elapsed_days}/{total_active_days}"
        status_color = "#FF9800"
        plan_status = "paused"
        
    elif current_date < start_date:
        completion_percentage = 0.0
        remaining_days = total_active_days
        is_started = False
        is_completed = False
        status_label = f"Commence le {start_date.strftime('%d/%m/%Y')}"
        status_color = "#9E9E9E"
        plan_status = "pending"
        
    elif current_date > end_date:
        completion_percentage = 100.0
        remaining_days = 0
        is_started = True
        is_completed = True
        status_label = f"Terminé le {end_date.strftime('%d/%m/%Y')}"
        status_color = "#4CAF50"
        plan_status = "completed"
        
    else:
        completion_percentage = round((effective_elapsed_days / total_active_days) * 100, 1) if total_active_days > 0 else 0
        remaining_days = max(0, total_active_days - effective_elapsed_days)
        is_started = True
        is_completed = False
        status_label = f"Jour {effective_elapsed_days}/{total_active_days}"
        status_color = "#2196F3"
        plan_status = "active"
    
    return {
        "total_calendar_days": (end_date - start_date).days + 1,
        "total_active_days": total_active_days,  # ✅ Jours selon days_of_week
        "elapsed_active_days": effective_elapsed_days,
        "raw_elapsed_days": elapsed_active_days,
        "paused_days": total_paused_days,
        "remaining_active_days": remaining_days,
        "completion_percentage": completion_percentage,
        "current_date": current_date.isoformat(),
        "current_active_day": current_active_day,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "is_started": is_started,
        "is_completed": is_completed,
        "status_label": status_label,
        "status_color": status_color,
        "plan_status": plan_status,
        "current_plan_status": current_plan_status,
        
        # ✅ Config de récurrence simplifiée
        "recurrence_config": {
            "days_of_week": days_of_week,
            "active_weekdays": len(days_of_week)
        },
        
        "pause_info": {
            "is_paused": current_plan_status == "paused",
            "total_paused_days": total_paused_days,
            "current_pause": get_current_pause_info(plan) if current_plan_status == "paused" else None
        }
    }

def calculate_active_days_by_weekdays(start_date, end_date, days_of_week):
    """
    Calculer tous les jours actifs basés uniquement sur days_of_week
    """
    from datetime import timedelta, date  # ✅ Ajouter l'import de 'date'
    
    active_days = []
    current_date = start_date
    day_number = 1
    
    while current_date <= end_date:
        weekday = current_date.weekday()  # 0=Lundi, 6=Dimanche 
        # ✅ Vérifier si ce jour de la semaine est dans la config
        if weekday in days_of_week:
            active_days.append({
                "day_number": day_number,
                "date": current_date,
                "date_iso": current_date.isoformat(),
                "weekday": weekday,
                "weekday_name": get_french_weekday(weekday),
                "is_today": current_date == date.today()  # ✅ Maintenant 'date' est défini
            })
            day_number += 1 
        current_date += timedelta(days=1) 
    return active_days

def calculate_paused_active_days(pause_history, active_days, current_date):
    """
    Calculer combien de jours actifs tombent dans les périodes de pause
    """
    from datetime import datetime
    
    paused_count = 0
    
    for pause in pause_history:
        pause_start = datetime.strptime(pause["pause_date"], "%Y-%m-%d").date()
        
        if pause["resume_date"]:
            pause_end = datetime.strptime(pause["resume_date"], "%Y-%m-%d").date()
        else:
            # Pause active - compter jusqu'à aujourd'hui
            pause_end = min(current_date, datetime.now().date())
        
        # Compter les jours actifs dans cette période de pause
        for active_day in active_days:
            active_day_date = active_day["date"]
            
            # Si le jour actif tombe dans la période de pause
            if pause_start <= active_day_date <= pause_end:
                paused_count += 1
    
    return paused_count

# def calculate_plan_progression_with_pauses(plan, current_date):
#     """
#     Calcul de progression avec prise en compte des pauses
#     """
#     from datetime import datetime, date, timedelta
    
#     # Gestion de la compatibilité avec les anciens plans (comme avant)
#     settings = plan.get("settings", {})
    
#     if "start_date" in settings and "end_date" in settings:
#         start_date_str = settings["start_date"]
#         end_date_str = settings["end_date"]
        
#         if isinstance(start_date_str, str):
#             start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
#         else:
#             start_date = start_date_str
            
#         if isinstance(end_date_str, str):
#             end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
#         else:
#             end_date = end_date_str
#     else:
#         # Ancien format - calculer à partir de created_at + duration_months
#         duration_months = settings.get("duration_months", 1)
#         created_at = plan.get("meta", {}).get("created_at")
        
#         if created_at:
#             if hasattr(created_at, 'date'):
#                 start_date = created_at.date()
#             else:
#                 start_date = datetime.strptime(str(created_at)[:10], "%Y-%m-%d").date()
            
#             end_date = start_date.replace(
#                 year=start_date.year + (start_date.month + duration_months - 1) // 12,
#                 month=(start_date.month + duration_months - 1) % 12 + 1
#             )
#         else:
#             start_date = current_date
#             end_date = current_date + timedelta(days=30 * duration_months)
    
#     # ✅ Récupérer les infos de pause
#     pause_history = plan.get("pause_history", [])
#     current_plan_status = plan.get("current_status", "active")
#     pause_adjustments = plan.get("pause_adjustments", {})
    
#     # ✅ Calculer le nombre de jours en pause
#     total_paused_days = calculate_total_paused_days(pause_history, current_date)
    
#     # ✅ Ajuster les calculs selon les pauses
#     total_days = (end_date - start_date).days + 1
    
#     # Jours effectivement écoulés (sans compter les pauses)
#     if current_date < start_date:
#         effective_elapsed_days = 0
#     else:
#         raw_elapsed_days = min((current_date - start_date).days + 1, total_days)
#         paused_days_in_elapsed = calculate_paused_days_in_period(pause_history, start_date, current_date)
#         effective_elapsed_days = max(0, raw_elapsed_days - paused_days_in_elapsed)
    
#     current_day = None
    
#     # ✅ Déterminer le statut du plan avec gestion des pauses
#     if current_plan_status == "paused":
#         # Plan en pause
#         completion_percentage = round((effective_elapsed_days / total_days) * 100, 1) if total_days > 0 else 0
#         remaining_days = max(0, total_days - effective_elapsed_days)
#         is_started = effective_elapsed_days > 0
#         is_completed = False
#         status_label = f"En pause - Jour {effective_elapsed_days}/{total_days}"
#         status_color = "#FF9800"
#         plan_status = "paused"
        
#         # Trouver le jour actuel dans le plan (sans compter les pauses)
#         current_day = effective_elapsed_days if effective_elapsed_days > 0 else 1
        
#     elif current_date < start_date:
#         # Plan pas encore commencé
#         effective_elapsed_days = 0
#         remaining_days = total_days
#         completion_percentage = 0.0
#         is_started = False
#         is_completed = False
#         status_label = f"Commence le {start_date.strftime('%d/%m/%Y')}"
#         status_color = "#9E9E9E"
#         plan_status = "pending"
        
#     elif current_date > end_date:
#         # Plan terminé
#         effective_elapsed_days = total_days
#         remaining_days = 0
#         completion_percentage = 100.0
#         is_started = True
#         is_completed = True
#         status_label = f"Terminé le {end_date.strftime('%d/%m/%Y')}"
#         status_color = "#4CAF50"
#         plan_status = "completed"
        
#     else:
#         # Plan en cours
#         completion_percentage = round((effective_elapsed_days / total_days) * 100, 1) if total_days > 0 else 0
#         remaining_days = max(0, total_days - effective_elapsed_days)
#         is_started = True
#         is_completed = False
#         status_label = f"Jour {effective_elapsed_days}/{total_days}"
#         status_color = "#2196F3"
#         current_day = effective_elapsed_days
#         plan_status = "active"
    
#     return {
#         "total_days": total_days,
#         "elapsed_days": effective_elapsed_days,  # ✅ Jours effectifs (sans pauses)
#         "raw_elapsed_days": min((current_date - start_date).days + 1, total_days) if current_date >= start_date else 0,  # ✅ Jours bruts
#         "paused_days": total_paused_days,  # ✅ Total jours en pause
#         "remaining_days": remaining_days,
#         "completion_percentage": completion_percentage,
#         "current_date": current_date.isoformat(),
#         "current_day": current_day,
#         "start_date": start_date.isoformat(),
#         "end_date": end_date.isoformat(),
#         "is_started": is_started,
#         "is_completed": is_completed,
#         "status_label": status_label,
#         "status_color": status_color,
#         "plan_status": plan_status,
#         "current_plan_status": current_plan_status,  # ✅ Statut système (active/paused/completed)
#         "days_until_start": max(0, (start_date - current_date).days) if current_date < start_date else 0,
#         "days_since_end": max(0, (current_date - end_date).days) if current_date > end_date else 0,
        
#         # ✅ Infos spécifiques aux pauses
#         "pause_info": {
#             "is_paused": current_plan_status == "paused",
#             "total_paused_days": total_paused_days,
#             "current_pause": get_current_pause_info(plan) if current_plan_status == "paused" else None
#         }
#     }

# def calculate_total_paused_days(pause_history, current_date):
#     """Calculer le nombre total de jours en pause"""
#     from datetime import datetime
    
#     total_days = 0
    
#     for pause in pause_history:
#         pause_start = datetime.strptime(pause["pause_date"], "%Y-%m-%d").date()
        
#         if pause["resume_date"]:
#             pause_end = datetime.strptime(pause["resume_date"], "%Y-%m-%d").date()
#         else:
#             # Pause active - compter jusqu'à aujourd'hui
#             pause_end = min(current_date, datetime.now().date())
        
#         if pause_end >= pause_start:
#             total_days += (pause_end - pause_start).days + 1
    
#     return total_days

# def calculate_paused_days_in_period(pause_history, start_date, end_date):
#     """Calculer les jours en pause dans une période donnée"""
#     from datetime import datetime
    
#     paused_days = 0
    
#     for pause in pause_history:
#         pause_start = datetime.strptime(pause["pause_date"], "%Y-%m-%d").date()
        
#         if pause["resume_date"]:
#             pause_end = datetime.strptime(pause["resume_date"], "%Y-%m-%d").date()
#         else:
#             # Pause active
#             pause_end = datetime.now().date()
        
#         # Calculer l'intersection entre la période de pause et la période demandée
#         overlap_start = max(pause_start, start_date)
#         overlap_end = min(pause_end, end_date)
        
#         if overlap_end >= overlap_start:
#             paused_days += (overlap_end - overlap_start).days + 1
    
#     return paused_days