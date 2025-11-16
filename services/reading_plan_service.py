# services/reading_plan_service.py

from models.reading_plan_model import ReadingPlanModel, UserReadingPlanModel, DocumentModel
from models.church_model import ChurchModel
from models.user_model import UserModel
from bson import ObjectId
from datetime import datetime, timedelta

def create_reading_plan_service(plan_data, creator_id, church_id=None):
    """Créer un nouveau plan de lecture"""
    # Ajouter les informations du créateur
    plan_data["creator_id"] = creator_id
    if church_id:
        plan_data["church_id"] = church_id
    
    # Déterminer le type de créateur
    user = UserModel.get_user_by_id(creator_id)
    if user and user.get("role") in ["admin", "pastor"]:
        plan_data["creator_type"] = user["role"]
    else:
        plan_data["creator_type"] = "user"
    
    result = ReadingPlanModel.create_plan(plan_data)
    return result, 201

def get_reading_plans_service(filters=None, page=1, per_page=20):
    """Récupérer les plans de lecture avec pagination"""
    skip = (page - 1) * per_page
    sort_by = filters.get("sort_by", "created_at") if filters else "created_at"
    
    plans = ReadingPlanModel.get_all_plans(filters, sort_by, skip, per_page)
    total = ReadingPlanModel.count_plans(filters)
    
    # Convertir les ObjectId
    for plan in plans:
        plan["_id"] = str(plan["_id"])
        plan["creator"]["user_id"] = str(plan["creator"]["user_id"])
        if plan["creator"].get("church_id"):
            plan["creator"]["church_id"] = str(plan["creator"]["church_id"])
        if plan.get("parent_plan_id"):
            plan["parent_plan_id"] = str(plan["parent_plan_id"])
    
    return {
        "data": plans,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

def get_reading_plan_detail_service(plan_id):
    """Récupérer les détails d'un plan de lecture"""
    plan = ReadingPlanModel.get_plan_by_id(plan_id)
    
    if not plan:
        return {"message": "Plan de lecture non trouvé"}, 404
    
    # Enrichir avec les informations de l'église créatrice
    if plan["creator"].get("church_id"):
        church = ChurchModel.get_church_by_id(plan["creator"]["church_id"])
        if church:
            plan["creator"]["church_name"] = church.get("name", "")
    
    return plan

def subscribe_to_plan_service(plan_id, user_id, church_id, customizations):
    """S'inscrire à un plan de lecture"""
    subscription_data = {
        "plan_id": plan_id,
        "user_id": user_id,
        "church_id": church_id,
        "customizations": customizations
    }
    
    result, status = UserReadingPlanModel.create_user_plan(subscription_data)
    return result, status

def get_user_plans_service(user_id, status=None):
    """Récupérer les plans d'un utilisateur"""
    return UserReadingPlanModel.get_user_plans(user_id, status)

def mark_reading_progress_service(user_plan_id, item_id, completion_data):
    """Marquer la progression de lecture"""
    result, status = UserReadingPlanModel.mark_item_completed(user_plan_id, item_id, completion_data)
    return result, status

def get_catch_up_options_service(user_plan_id):
    """Récupérer les options de rattrapage"""
    return UserReadingPlanModel.get_catch_up_options(user_plan_id)

def apply_catch_up_strategy_service(user_plan_id, strategy, params):
    """Appliquer une stratégie de rattrapage"""
    result, status = UserReadingPlanModel.apply_catch_up_strategy(user_plan_id, strategy, params)
    return result, status

def quick_create_plan_service(template_data, user_id, church_id):
    """Création rapide de plan avec templates"""
    source = template_data['source']
    
    if source['type'] == 'document':
        # Générer un plan à partir d'un document
        doc_id = source['document_id']
        helper_data = DocumentModel.get_plan_helper(doc_id)
        
        if isinstance(helper_data, tuple):
            return helper_data
        
        strategy = source['strategy']
        daily_target = source['daily_target']
        
        if strategy == 'time_based':
            total_time = helper_data['document_info']['estimated_total_time']
            duration_days = max(1, total_time // daily_target)
        elif strategy == 'page_based':
            total_pages = helper_data['document_info']['total_pages']
            duration_days = max(1, total_pages // daily_target)
        else:
            duration_days = 30  # par défaut
        
        # Générer les content_items
        content_items = []
        document = DocumentModel.get_document_by_id(doc_id)
        total_pages = helper_data['document_info']['total_pages']
        
        for day in range(1, duration_days + 1):
            if strategy == 'page_based':
                start_page = (day - 1) * daily_target + 1
                end_page = min(day * daily_target, total_pages)
                
                content_items.append({
                    'item_id': f'day_{day}_doc',
                    'day': day,
                    'order': 1,
                    'content_type': 'document_section',
                    'content_ref': {
                        'type': 'document_section',
                        'resource_id': str(doc_id),
                        'specific_ref': f'pages:{start_page}-{end_page}',
                        'page_ref': f'pages:{start_page}-{end_page}',
                        'display_ref': f"{document['title']} - Pages {start_page}-{end_page}"
                    },
                    'title': f"Lecture jour {day} - Pages {start_page}-{end_page}",
                    'estimated_time': daily_target * 2 if strategy == 'page_based' else daily_target,
                    'is_optional': False
                })
        
        # Créer le plan
        plan_data = {
            'title': template_data.get('plan_info', {}).get('title') or f"Plan de lecture - {document['title']}",
            'description': f"Plan généré automatiquement pour {document['title']}",
            'category': 'study',
            'visibility': template_data.get('plan_info', {}).get('visibility', 'private'),
            'duration_days': duration_days,
            'estimated_daily_time': daily_target if strategy == 'time_based' else daily_target * 2,
            'difficulty_level': 'intermediate',
            'tags': ['auto-generated', 'document'],
            'content_items': content_items,
            'quiz_integration': {'has_quizzes': False}
        }
        
        # Créer le plan
        result, status = create_reading_plan_service(plan_data, user_id, church_id)
        if status != 201:
            return result, status
        
        plan_id = result['plan_id']
        
        # Auto-inscription
        preferences = template_data.get('preferences', {})
        customizations = {
            'daily_reminder_time': preferences.get('reminder_time', '07:00'),
            'reminder_days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'] if not preferences.get('weekend_reading', True) else ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
            'pace': 'normal',
            'bible_version': 'louis_segond'
        }
        
        user_plan_result, user_plan_status = subscribe_to_plan_service(plan_id, user_id, church_id, customizations)
        
        if user_plan_status != 201:
            return user_plan_result, user_plan_status
        
        return {
            'plan_id': plan_id,
            'user_plan_id': user_plan_result['user_plan_id'],
            'generated_schedule': content_items[:5],  # Aperçu des 5 premiers jours
            'summary': {
                'total_duration': duration_days,
                'daily_average_time': plan_data['estimated_daily_time'],
                'completion_date': (datetime.utcnow() + timedelta(days=duration_days)).isoformat()
            }
        }, 201
    
    return {"message": "Type de template non supporté"}, 400

# Services pour les documents
def create_document_service(document_data, file_info, uploaded_by):
    """Créer un nouveau document"""
    result = DocumentModel.create_document(document_data, file_info, uploaded_by)
    return result, 201

def get_documents_for_plans_service(filters=None):
    """Récupérer les documents disponibles pour les plans"""
    return DocumentModel.get_documents_for_plans(filters)

def get_document_plan_helper_service(document_id):
    """Aide à la configuration d'un plan depuis un document"""
    result = DocumentModel.get_plan_helper(document_id)
    if isinstance(result, tuple):
        return result
    return result

def update_document_structure_service(document_id, structure_data):
    """Mettre à jour la structure d'un document"""
    result, status = DocumentModel.update_structure(document_id, structure_data)
    return result, status