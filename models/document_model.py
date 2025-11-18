import os
from bson import ObjectId
from datetime import datetime, timedelta
from extensions import mongo

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