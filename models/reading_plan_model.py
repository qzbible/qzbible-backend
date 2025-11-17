# models/reading_plan_model.py
import os
from bson import ObjectId
from datetime import datetime, timedelta
from extensions import mongo

class ReadingPlanModel:
    """Modèle pour les plans de lecture"""
    
    collection = mongo.db.reading_plans
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.reading_plans
    
    @staticmethod
    def create_plan(data):
        """Créer un nouveau plan de lecture"""
        plan = {
            "title": data["title"],
            "description": data.get("description", ""),
            "category": data["category"],
            "type": data.get("type", "user_created"),
            "creator": {
                "user_id": ObjectId(data["creator_id"]),
                "creator_type": data.get("creator_type", "user"),
                "church_id": ObjectId(data.get("church_id")) if data.get("church_id") else None
            },
            "visibility": data.get("visibility", "private"),
            "duration_days": data["duration_days"],
            "estimated_daily_time": data["estimated_daily_time"],
            "difficulty_level": data.get("difficulty_level", "intermediate"),
            "tags": data.get("tags", []),
            "content_items": data["content_items"],
            "quiz_integration": data.get("quiz_integration", {"has_quizzes": False}),
            "version": "1.0.0",
            "is_copy": data.get("is_copy", False),
            "parent_plan_id": ObjectId(data["parent_plan_id"]) if data.get("parent_plan_id") else None,
            "stats": {
                "subscribers": 0,
                "completions": 0,
                "average_rating": 0.0
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = ReadingPlanModel.get_collection().insert_one(plan)
        return {
            "message": "Plan de lecture créé avec succès",
            "plan_id": str(result.inserted_id)
        }
    
    @staticmethod
    def get_plan_by_id(plan_id):
        """Récupérer un plan par ID"""
        plan = ReadingPlanModel.get_collection().find_one({"_id": ObjectId(plan_id)})
        if plan:
            plan["_id"] = str(plan["_id"])
            plan["creator"]["user_id"] = str(plan["creator"]["user_id"])
            if plan["creator"].get("church_id"):
                plan["creator"]["church_id"] = str(plan["creator"]["church_id"])
            if plan.get("parent_plan_id"):
                plan["parent_plan_id"] = str(plan["parent_plan_id"])
        return plan
    
    @staticmethod
    def get_all_plans(filters=None, sort_by="created_at", skip=0, limit=20):
        """Récupérer tous les plans avec filtres"""
        query = {}
        
        if filters:
            if filters.get("category"):
                query["category"] = filters["category"]
            if filters.get("difficulty"):
                query["difficulty_level"] = filters["difficulty"]
            if filters.get("creator_type"):
                query["creator.creator_type"] = filters["creator_type"]
            if filters.get("duration_range"):
                min_days, max_days = map(int, filters["duration_range"].split('-'))
                query["duration_days"] = {"$gte": min_days, "$lte": max_days}
            if filters.get("tags"):
                query["tags"] = {"$in": filters["tags"]}
            if filters.get("search"):
                query["$or"] = [
                    {"title": {"$regex": filters["search"], "$options": "i"}},
                    {"description": {"$regex": filters["search"], "$options": "i"}},
                    {"tags": {"$regex": filters["search"], "$options": "i"}}
                ]
        
        # Exclure les plans privés (sauf si on filtre par créateur)
        if not filters or not filters.get("creator_id"):
            query["visibility"] = {"$in": ["public", "church_only"]}
        
        sort_field = "stats.subscribers" if sort_by == "popular" else \
                     "stats.average_rating" if sort_by == "rating" else \
                     "created_at"
        sort_order = -1
        
        plans = ReadingPlanModel.get_collection().find(query).sort(sort_field, sort_order).skip(skip).limit(limit)
        return list(plans)
    
    @staticmethod
    def count_plans(filters=None):
        """Compter les plans avec filtres"""
        query = {}
        
        if filters:
            if filters.get("category"):
                query["category"] = filters["category"]
            if filters.get("difficulty"):
                query["difficulty_level"] = filters["difficulty"]
            if filters.get("creator_type"):
                query["creator.creator_type"] = filters["creator_type"]
            if filters.get("duration_range"):
                min_days, max_days = map(int, filters["duration_range"].split('-'))
                query["duration_days"] = {"$gte": min_days, "$lte": max_days}
            if filters.get("tags"):
                query["tags"] = {"$in": filters["tags"]}
            if filters.get("search"):
                query["$or"] = [
                    {"title": {"$regex": filters["search"], "$options": "i"}},
                    {"description": {"$regex": filters["search"], "$options": "i"}},
                    {"tags": {"$regex": filters["search"], "$options": "i"}}
                ]
        
        if not filters or not filters.get("creator_id"):
            query["visibility"] = {"$in": ["public", "church_only"]}
        
        return ReadingPlanModel.get_collection().count_documents(query)
    
    @staticmethod
    def update_plan_stats(plan_id, action):
        """Mettre à jour les statistiques du plan"""
        update_data = {}
        if action == "subscribe":
            update_data = {"$inc": {"stats.subscribers": 1}}
        elif action == "complete":
            update_data = {"$inc": {"stats.completions": 1}}
        
        if update_data:
            ReadingPlanModel.get_collection().update_one(
                {"_id": ObjectId(plan_id)},
                update_data
            )


class UserReadingPlanModel:
    """Modèle pour les plans de lecture des utilisateurs"""
    
    collection = mongo.db.user_reading_plans
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.user_reading_plans
    
    @staticmethod
    def create_user_plan(data):
        """Créer une souscription utilisateur à un plan"""
        # Vérifier si déjà inscrit
        existing = UserReadingPlanModel.get_collection().find_one({
            "user_id": ObjectId(data["user_id"]),
            "plan_id": ObjectId(data["plan_id"]),
            "status": {"$in": ["active", "paused"]}
        })
        
        if existing:
            return {"message": "Utilisateur déjà inscrit à ce plan"}, 400
        
        # Récupérer le plan original pour snapshot
        plan = ReadingPlanModel.get_plan_by_id(data["plan_id"])
        if not plan:
            return {"message": "Plan non trouvé"}, 404
        
        user_plan = {
            "user_id": ObjectId(data["user_id"]),
            "plan_id": ObjectId(data["plan_id"]),
            "church_id": ObjectId(data["church_id"]) if data.get("church_id") else None,
            "customizations": data.get("customizations", {
                "daily_reminder_time": "07:00",
                "reminder_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "pace": "normal",
                "bible_version": "louis_segond",
                "catch_up_mode": "extend_duration"
            }),
            "plan_snapshot": {
                "content_items": plan["content_items"],
                "original_version": plan["version"]
            },
            "progress": {
                "started_at": datetime.utcnow(),
                "current_day": 1,
                "completed_items": [],
                "missed_days": [],
                "completion_percentage": 0.0,
                "estimated_completion_date": UserReadingPlanModel._calculate_completion_date(
                    plan["duration_days"], 
                    data.get("customizations", {}).get("pace", "normal")
                ),
                "daily_progress": {}
            },
            "status": "active",
            "created_at": datetime.utcnow()
        }
        
        result = UserReadingPlanModel.get_collection().insert_one(user_plan)
        
        # Mettre à jour les stats du plan
        ReadingPlanModel.update_plan_stats(data["plan_id"], "subscribe")
        
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
        
        user_plans = list(UserReadingPlanModel.get_collection().find(query).sort("created_at", -1))
        
        # Enrichir avec les détails du plan
        for user_plan in user_plans:
            user_plan["_id"] = str(user_plan["_id"])
            user_plan["user_id"] = str(user_plan["user_id"])
            user_plan["plan_id"] = str(user_plan["plan_id"])
            if user_plan.get("church_id"):
                user_plan["church_id"] = str(user_plan["church_id"])
            
            # Ajouter les détails du plan
            plan = ReadingPlanModel.get_plan_by_id(user_plan["plan_id"])
            if plan:
                user_plan["plan_details"] = {
                    "title": plan["title"],
                    "description": plan["description"],
                    "category": plan["category"]
                }
        
        return user_plans
    
    @staticmethod
    def mark_item_completed(user_plan_id, item_id, completion_data):
        """Marquer un élément comme complété"""
        user_plan = UserReadingPlanModel.get_collection().find_one({"_id": ObjectId(user_plan_id)})
        if not user_plan:
            return {"message": "Plan utilisateur non trouvé"}, 404
        
        # Trouver l'item dans le plan
        item = next((item for item in user_plan['plan_snapshot']['content_items'] 
                    if item['item_id'] == item_id), None)
        if not item:
            return {"message": "Élément non trouvé dans le plan"}, 404
        
        day = item['day']
        current_time = datetime.utcnow()
        
        # Mettre à jour le progrès quotidien
        daily_key = f"day_{day}"
        if daily_key not in user_plan['progress']['daily_progress']:
            user_plan['progress']['daily_progress'][daily_key] = {
                'started_at': current_time,
                'completed_at': None,
                'items': []
            }
        
        # Ajouter/mettre à jour l'item complété
        item_progress = {
            'item_id': item_id,
            'completed': completion_data.get('completed', True),
            'completed_at': current_time,
            'time_spent': completion_data.get('time_spent', 0),
            'notes': completion_data.get('notes', ''),
            'rating': completion_data.get('rating')
        }
        
        # Vérifier si l'item existe déjà
        existing_item_idx = next((i for i, existing in enumerate(
            user_plan['progress']['daily_progress'][daily_key]['items'])
            if existing['item_id'] == item_id), None)
        
        if existing_item_idx is not None:
            user_plan['progress']['daily_progress'][daily_key]['items'][existing_item_idx] = item_progress
        else:
            user_plan['progress']['daily_progress'][daily_key]['items'].append(item_progress)
        
        # Vérifier si tous les items du jour sont complétés
        day_items = [item for item in user_plan['plan_snapshot']['content_items'] 
                    if item['day'] == day]
        completed_day_items = user_plan['progress']['daily_progress'][daily_key]['items']
        
        if len(completed_day_items) == len(day_items):
            user_plan['progress']['daily_progress'][daily_key]['completed_at'] = current_time
            user_plan['progress']['current_day'] = day + 1
        
        # Calculer le pourcentage de completion
        total_items = len(user_plan['plan_snapshot']['content_items'])
        completed_items = sum(len(day_data['items']) for day_data in 
                            user_plan['progress']['daily_progress'].values())
        completion_percentage = (completed_items / total_items) * 100
        
        # Vérifier si le plan est complété
        if completion_percentage >= 100:
            user_plan['status'] = 'completed'
            ReadingPlanModel.update_plan_stats(user_plan['plan_id'], "complete")
        
        # Mettre à jour en base
        UserReadingPlanModel.get_collection().update_one(
            {'_id': ObjectId(user_plan_id)},
            {
                '$set': {
                    f'progress.daily_progress.{daily_key}': user_plan['progress']['daily_progress'][daily_key],
                    'progress.current_day': user_plan['progress']['current_day'],
                    'progress.completion_percentage': completion_percentage,
                    'status': user_plan['status']
                }
            }
        )
        
        return {
            "message": "Progression mise à jour",
            "completion_percentage": completion_percentage,
            "current_day": user_plan['progress']['current_day'],
            "completed": user_plan['status'] == 'completed'
        }, 200
    
    @staticmethod
    def get_catch_up_options(user_plan_id):
        """Calculer les options de rattrapage"""
        user_plan = UserReadingPlanModel.get_collection().find_one({"_id": ObjectId(user_plan_id)})
        if not user_plan:
            return {"message": "Plan utilisateur non trouvé"}, 404
        
        days_since_start = (datetime.utcnow() - user_plan['progress']['started_at']).days + 1
        current_day = user_plan['progress']['current_day']
        days_behind = max(0, days_since_start - current_day)
        
        if days_behind == 0:
            return {'days_behind': 0, 'options': []}
        
        options = []
        
        # Option 1: Étendre la durée
        options.append({
            'type': 'extend_duration',
            'additional_days': days_behind,
            'new_end_date': (user_plan['progress']['estimated_completion_date'] + 
                           timedelta(days=days_behind)).isoformat(),
            'description': f'Étendre le plan de {days_behind} jours'
        })
        
        # Option 2: Compresser les lectures
        if days_behind <= 10:
            increase_percent = min(50, (days_behind / (current_day or 1)) * 100)
            options.append({
                'type': 'compress_readings',
                'daily_increase': f'{increase_percent:.0f}%',
                'description': f'Augmenter le contenu quotidien de {increase_percent:.0f}%'
            })
        
        # Option 3: Ignorer les éléments optionnels
        optional_items = [item for item in user_plan['plan_snapshot']['content_items'] 
                         if item.get('is_optional', False)]
        if optional_items:
            options.append({
                'type': 'skip_optional',
                'items_to_skip': len(optional_items),
                'days_saved': len(optional_items) // 2,
                'description': f'Ignorer {len(optional_items)} éléments optionnels'
            })
        
        return {
            'days_behind': days_behind,
            'options': options
        }
    
    @staticmethod
    def apply_catch_up_strategy(user_plan_id, strategy, params=None):
        """Appliquer une stratégie de rattrapage"""
        user_plan = UserReadingPlanModel.get_collection().find_one({"_id": ObjectId(user_plan_id)})
        if not user_plan:
            return {"message": "Plan utilisateur non trouvé"}, 404
        
        update_data = {}
        
        if strategy == 'extend_duration':
            additional_days = params.get('additional_days', 0)
            new_completion_date = (user_plan['progress']['estimated_completion_date'] + 
                                 timedelta(days=additional_days))
            update_data['progress.estimated_completion_date'] = new_completion_date
            
        elif strategy == 'compress_readings':
            update_data['customizations.catch_up_mode'] = 'compress_readings'
            update_data['customizations.compression_factor'] = params.get('factor', 1.2)
            
        elif strategy == 'skip_optional':
            update_data['customizations.skip_optional_items'] = True
        
        UserReadingPlanModel.get_collection().update_one(
            {'_id': ObjectId(user_plan_id)},
            {'$set': update_data}
        )
        
        return {
            "message": "Stratégie de rattrapage appliquée",
            "strategy_applied": strategy
        }, 200
    
    @staticmethod
    def _calculate_completion_date(duration_days, pace):
        """Calculer la date de fin estimée"""
        multipliers = {'slow': 1.5, 'normal': 1.0, 'fast': 0.8}
        actual_duration = int(duration_days * multipliers.get(pace, 1.0))
        return datetime.utcnow() + timedelta(days=actual_duration)


class DocumentModel:
    """Modèle pour les documents (livres PDF)"""
    
    collection = mongo.db.documents
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.documents
    
    @staticmethod
    def create_document(data, file_info, uploaded_by):
        """Créer un nouveau document"""
        document = {
            "title": data["title"],
            "author": data["author"],
            "type": "pdf",
            "category": data["category"],
            "language": data.get("language", "fr"),
            "description": data.get("description", ""),
            "tags": data.get("tags", []),
            "file_info": file_info,
            "structure": data.get("structure", {
                "total_pages": 0,
                "chapters": [],
                "sections": []
            }),
            "metadata": {
                "difficulty_level": data.get("difficulty_level", "intermediate"),
                "target_audience": data.get("target_audience", "all"),
                "isbn": data.get("isbn")
            },
            "access": {
                "visibility": data.get("visibility", "public"),
                "church_id": ObjectId(data["church_id"]) if data.get("church_id") else None,
                "uploaded_by": ObjectId(uploaded_by),
                "permissions": ["read", "download", "share"]
            },
            "stats": {
                "download_count": 0,
                "view_count": 0,
                "plans_using": 0
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = DocumentModel.get_collection().insert_one(document)
        return {
            "message": "Document créé avec succès",
            "document_id": str(result.inserted_id)
        }
    
    @staticmethod
    def get_document_by_id(document_id):
        """Récupérer un document par ID"""
        doc = DocumentModel.get_collection().find_one({"_id": ObjectId(document_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
            doc["access"]["uploaded_by"] = str(doc["access"]["uploaded_by"])
            if doc["access"].get("church_id"):
                doc["access"]["church_id"] = str(doc["access"]["church_id"])
        return doc
    
    @staticmethod
    def get_documents_for_plans(filters=None):
        """Récupérer les documents disponibles pour les plans"""
        query = {}
        
        if filters:
            if filters.get("category"):
                query["category"] = filters["category"]
            if filters.get("language"):
                query["language"] = filters["language"]
            if filters.get("has_page_numbers"):
                query["structure.total_pages"] = {"$gt": 0}
            if filters.get("min_pages"):
                query["structure.total_pages"] = {"$gte": int(filters["min_pages"])}
        
        # Seulement les documents publics ou d'église
        query["access.visibility"] = {"$in": ["public", "church_only"]}
        
        documents = list(DocumentModel.get_collection().find(query).sort("created_at", -1))
        
        # # Ajouter des estimations de lecture
        # for doc in documents:
        #     doc["_id"] = str(doc["_id"])
        #     doc["access"]["uploaded_by"] = str(doc["access"]["uploaded_by"])
        #     if doc["access"].get("church_id"):
        #         doc["access"]["church_id"] = str(doc["access"]["church_id"])
            
        #     if 'structure' in doc and 'total_pages' in doc['structure']:
        #         pages = doc['structure']['total_pages']
        #         doc['reading_estimates'] = {
        #             'fast': f"{max(1, pages // 15)} jours ({15} pages/jour)",
        #             'normal': f"{max(1, pages // 5)} jours (5 pages/jour)",
        #             'slow': f"{max(1, pages // 3)} jours (3 pages/jour)"
        #         }

        # Ajouter des estimations de lecture et chemin absolu
        for doc in documents:
            doc["_id"] = str(doc["_id"])
            doc["access"]["uploaded_by"] = str(doc["access"]["uploaded_by"])
            if doc["access"].get("church_id"):
                doc["access"]["church_id"] = str(doc["access"]["church_id"])
            
            # Ajouter le chemin absolu du fichier
            if doc.get("file_info", {}).get("file_path"):
                doc["absolute_file_path"] = os.path.abspath(doc["file_info"]["file_path"])
            else:
                doc["absolute_file_path"] = None
            
            if 'structure' in doc and 'total_pages' in doc['structure']:
                pages = doc['structure']['total_pages']
                doc['reading_estimates'] = {
                    'fast': f"{max(1, pages // 15)} jours ({15} pages/jour)",
                    'normal': f"{max(1, pages // 5)} jours (5 pages/jour)",
                    'slow': f"{max(1, pages // 3)} jours (3 pages/jour)"
                }
        
        return documents
    
    @staticmethod
    def get_plan_helper(document_id):
        """Aide à la configuration d'un plan depuis un document"""
        doc = DocumentModel.get_document_by_id(document_id)
        if not doc:
            return {"message": "Document non trouvé"}, 404
        
        total_pages = doc.get('structure', {}).get('total_pages', 0)
        if total_pages == 0:
            return {"message": "Structure du document non disponible"}, 400
        
        estimated_total_time = total_pages * 2  # ~2 minutes par page
        
        suggestions = {
            'daily_reading_options': [
                {
                    'type': 'time_based',
                    'daily_time': 15,
                    'estimated_duration': max(1, estimated_total_time // 15),
                    'pages_per_day': f"~{max(1, total_pages * 15 // estimated_total_time)} pages"
                },
                {
                    'type': 'page_based',
                    'pages_per_day': 5,
                    'estimated_duration': max(1, total_pages // 5),
                    'daily_time': "~10 minutes"
                }
            ],
            'quick_templates': [
                {
                    'name': 'Lecture rapide (2 semaines)',
                    'daily_commitment': '20 minutes',
                    'structure': f'~{max(1, total_pages // 14)} pages par jour'
                },
                {
                    'name': 'Étude approfondie (1 mois)', 
                    'daily_commitment': '10 minutes',
                    'structure': f'~{max(1, total_pages // 30)} pages par jour'
                }
            ]
        }
        
        return {
            'document_info': {
                'title': doc['title'],
                'total_pages': total_pages,
                'estimated_total_time': estimated_total_time
            },
            'suggestions': suggestions
        }
    
    @staticmethod
    def update_structure(document_id, structure_data):
        """Mettre à jour la structure d'un document"""
        result = DocumentModel.get_collection().update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "structure": structure_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            return {"message": "Document non trouvé"}, 404
        
        return {"message": "Structure mise à jour avec succès"}, 200