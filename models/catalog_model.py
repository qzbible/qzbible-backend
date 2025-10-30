# models/catalog_model.py

from bson import ObjectId
from datetime import datetime
from extensions import mongo

class CatalogModel:
    
    collection = mongo.db.catalog
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.catalog
    
    @staticmethod
    def publish_to_catalog(data):
        """
        Publie du contenu au catalogue public.
        
        :param data: dict contenant les informations du contenu
        :return: dict contenant le message de succès et l'ID
        """
        catalog_item = {
            "content_type": data["content_type"],
            "content_id": ObjectId(data["content_id"]),
            "church_id": ObjectId(data["church_id"]),
            "church_name": data.get("church_name", ""),
            "title": data["title"],
            "description": data.get("description", ""),
            "preview": data.get("preview", {
                "chapters_count": 0,
                "quiz_count": 0,
                "avg_rating": 0
            }),
            "tags": data.get("tags", []),
            "downloads_count": 0,
            "rating": 0.0,
            "ratings_count": 0,
            "published_at": datetime.utcnow()
        }
        
        result = CatalogModel.get_collection().insert_one(catalog_item)
        
        return {
            "message": "Contenu publié au catalogue avec succès",
            "catalog_item_id": str(result.inserted_id)
        }
    
    @staticmethod
    def get_catalog_item_by_id(catalog_item_id):
        """
        Récupère un élément du catalogue par son ID.
        """
        item = CatalogModel.get_collection().find_one({"_id": ObjectId(catalog_item_id)})
        if item:
            item["_id"] = str(item["_id"])
            item["content_id"] = str(item["content_id"])
            item["church_id"] = str(item["church_id"])
        
        return item
    
    @staticmethod
    def get_all_catalog_items(filters=None, sort_by="downloads", skip=0, limit=20):
        """
        Récupère tous les éléments du catalogue avec filtres et pagination.
        """
        query = {}
        
        if filters:
            if filters.get("content_type"):
                query["content_type"] = filters["content_type"]
            
            if filters.get("tags"):
                query["tags"] = {"$in": filters["tags"]}
            
            if filters.get("min_rating"):
                query["rating"] = {"$gte": filters["min_rating"]}
            
            if filters.get("search"):
                query["$or"] = [
                    {"title": {"$regex": filters["search"], "$options": "i"}},
                    {"description": {"$regex": filters["search"], "$options": "i"}},
                    {"tags": {"$regex": filters["search"], "$options": "i"}}
                ]
        
        # Déterminer le tri
        sort_field = "downloads_count" if sort_by == "downloads" else \
                     "rating" if sort_by == "rating" else \
                     "published_at"
        sort_order = -1  # Décroissant
        
        items = CatalogModel.get_collection().find(query).sort(sort_field, sort_order).skip(skip).limit(limit)
        return list(items)
    
    @staticmethod
    def count_catalog_items(filters=None):
        """
        Compte le nombre d'éléments du catalogue avec filtres.
        """
        query = {}
        
        if filters:
            if filters.get("content_type"):
                query["content_type"] = filters["content_type"]
            
            if filters.get("tags"):
                query["tags"] = {"$in": filters["tags"]}
            
            if filters.get("min_rating"):
                query["rating"] = {"$gte": filters["min_rating"]}
            
            if filters.get("search"):
                query["$or"] = [
                    {"title": {"$regex": filters["search"], "$options": "i"}},
                    {"description": {"$regex": filters["search"], "$options": "i"}},
                    {"tags": {"$regex": filters["search"], "$options": "i"}}
                ]
        
        return CatalogModel.get_collection().count_documents(query)
    
    @staticmethod
    def get_catalog_items_by_church(church_id):
        """
        Récupère tous les éléments publiés par une église.
        """
        items = CatalogModel.get_collection().find({
            "church_id": ObjectId(church_id)
        }).sort("published_at", -1)
        return list(items)
    
    @staticmethod
    def check_if_published(content_type, content_id):
        """
        Vérifie si un contenu est déjà publié au catalogue.
        """
        item = CatalogModel.get_collection().find_one({
            "content_type": content_type,
            "content_id": ObjectId(content_id)
        })
        return item is not None
    
    @staticmethod
    def increment_downloads(catalog_item_id):
        """
        Incrémente le compteur de téléchargements.
        """
        result = CatalogModel.get_collection().update_one(
            {"_id": ObjectId(catalog_item_id)},
            {"$inc": {"downloads_count": 1}}
        )
        return result.modified_count > 0
    
    @staticmethod
    def update_rating(catalog_item_id, new_rating):
        """
        Met à jour la note moyenne d'un élément.
        """
        # Récupérer l'élément actuel
        item = CatalogModel.get_catalog_item_by_id(catalog_item_id)
        if not item:
            return False
        
        current_rating = item.get("rating", 0)
        ratings_count = item.get("ratings_count", 0)
        
        # Calculer la nouvelle moyenne
        total_rating = current_rating * ratings_count + new_rating
        new_ratings_count = ratings_count + 1
        new_avg_rating = total_rating / new_ratings_count
        
        result = CatalogModel.get_collection().update_one(
            {"_id": ObjectId(catalog_item_id)},
            {
                "$set": {
                    "rating": round(new_avg_rating, 2),
                    "ratings_count": new_ratings_count
                }
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def unpublish_from_catalog(catalog_item_id):
        """
        Retire un élément du catalogue.
        """
        result = CatalogModel.get_collection().delete_one({"_id": ObjectId(catalog_item_id)})
        
        return {
            "message": "Contenu retiré du catalogue avec succès",
            "deleted_count": result.deleted_count
        }
    
    @staticmethod
    def get_popular_tags(limit=20):
        """
        Récupère les tags les plus populaires.
        """
        pipeline = [
            {"$unwind": "$tags"},
            {"$group": {
                "_id": "$tags",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit},
            {"$project": {
                "tag": "$_id",
                "count": 1,
                "_id": 0
            }}
        ]
        
        return list(CatalogModel.get_collection().aggregate(pipeline))
    
    @staticmethod
    def get_catalog_stats():
        """
        Récupère les statistiques générales du catalogue.
        """
        pipeline = [
            {"$group": {
                "_id": "$content_type",
                "count": {"$sum": 1},
                "total_downloads": {"$sum": "$downloads_count"},
                "avg_rating": {"$avg": "$rating"}
            }}
        ]
        
        stats_by_type = list(CatalogModel.get_collection().aggregate(pipeline))
        
        # Stats globales
        total_items = CatalogModel.get_collection().count_documents({})
        total_downloads = sum(s.get("total_downloads", 0) for s in stats_by_type)
        
        return {
            "total_items": total_items,
            "total_downloads": total_downloads,
            "by_type": stats_by_type
        }
    
    @staticmethod
    def search_catalog(search_term, limit=20):
        """
        Recherche dans le catalogue.
        """
        query = {
            "$or": [
                {"title": {"$regex": search_term, "$options": "i"}},
                {"description": {"$regex": search_term, "$options": "i"}},
                {"tags": {"$regex": search_term, "$options": "i"}},
                {"church_name": {"$regex": search_term, "$options": "i"}}
            ]
        }
        
        items = CatalogModel.get_collection().find(query).sort("downloads_count", -1).limit(limit)
        return list(items)


class CatalogRatingModel:
    """Model pour les notes/avis des éléments du catalogue"""
    
    collection = mongo.db.catalog_ratings
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.catalog_ratings
    
    @staticmethod
    def add_rating(data):
        """
        Ajoute une note/avis pour un élément du catalogue.
        """
        # Vérifier si l'utilisateur a déjà noté cet élément
        existing = CatalogRatingModel.get_collection().find_one({
            "catalog_item_id": ObjectId(data["catalog_item_id"]),
            "user_id": ObjectId(data["user_id"])
        })
        
        if existing:
            # Mettre à jour la note existante
            result = CatalogRatingModel.get_collection().update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "rating": data["rating"],
                        "comment": data.get("comment", ""),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return {
                "message": "Note mise à jour avec succès",
                "rating_id": str(existing["_id"]),
                "updated": True
            }
        else:
            # Créer une nouvelle note
            rating = {
                "catalog_item_id": ObjectId(data["catalog_item_id"]),
                "user_id": ObjectId(data["user_id"]),
                "church_id": ObjectId(data["church_id"]),
                "rating": data["rating"],
                "comment": data.get("comment", ""),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = CatalogRatingModel.get_collection().insert_one(rating)
            
            return {
                "message": "Note ajoutée avec succès",
                "rating_id": str(result.inserted_id),
                "updated": False
            }
    
    @staticmethod
    def get_ratings_by_catalog_item(catalog_item_id, skip=0, limit=10):
        """
        Récupère les notes/avis d'un élément du catalogue.
        """
        ratings = CatalogRatingModel.get_collection().find({
            "catalog_item_id": ObjectId(catalog_item_id)
        }).sort("created_at", -1).skip(skip).limit(limit)
        return list(ratings)
    
    @staticmethod
    def get_user_rating(catalog_item_id, user_id):
        """
        Récupère la note d'un utilisateur pour un élément.
        """
        rating = CatalogRatingModel.get_collection().find_one({
            "catalog_item_id": ObjectId(catalog_item_id),
            "user_id": ObjectId(user_id)
        })
        return rating


class CatalogDownloadModel:
    """Model pour tracker les téléchargements depuis le catalogue"""
    
    collection = mongo.db.catalog_downloads
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.catalog_downloads
    
    @staticmethod
    def record_download(data):
        """
        Enregistre un téléchargement.
        """
        download = {
            "catalog_item_id": ObjectId(data["catalog_item_id"]),
            "church_id": ObjectId(data["church_id"]),
            "downloaded_by": ObjectId(data["downloaded_by"]),
            "content_type": data["content_type"],
            "content_id": ObjectId(data["content_id"]),
            "downloaded_at": datetime.utcnow()
        }
        
        result = CatalogDownloadModel.get_collection().insert_one(download)
        
        return {
            "message": "Téléchargement enregistré",
            "download_id": str(result.inserted_id)
        }
    
    @staticmethod
    def get_downloads_by_church(church_id):
        """
        Récupère l'historique des téléchargements d'une église.
        """
        downloads = CatalogDownloadModel.get_collection().find({
            "church_id": ObjectId(church_id)
        }).sort("downloaded_at", -1)
        return list(downloads)
    
    @staticmethod
    def check_if_downloaded(catalog_item_id, church_id):
        """
        Vérifie si une église a déjà téléchargé un élément.
        """
        download = CatalogDownloadModel.get_collection().find_one({
            "catalog_item_id": ObjectId(catalog_item_id),
            "church_id": ObjectId(church_id)
        })
        return download is not None