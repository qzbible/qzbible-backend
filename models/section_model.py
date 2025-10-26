# models/section_model.py

from bson import ObjectId
from datetime import datetime
from extensions import mongo

class SectionModel:
    
    collection = mongo.db.sections
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.sections
    
    @staticmethod
    def create_section(data):
        """
        Crée une nouvelle section avec les informations fournies.
        
        :param data: dict contenant 'church_id', 'title', 'description', 'order', 'is_sequential', etc.
        :return: dict contenant le message de succès et l'ID de la section créée
        """
        section = {
            "church_id": ObjectId(data["church_id"]),
            "title": data["title"],
            "description": data.get("description", ""),
            "order": data.get("order", 1),
            "is_sequential": data.get("is_sequential", True),
            "icon": data.get("icon", None),
            "is_public": data.get("is_public", False),
            "is_template": data.get("is_template", False),
            "source_section_id": ObjectId(data["source_section_id"]) if data.get("source_section_id") else None,
            "stats": {
                "total_chapters": 0,
                "total_quiz": 0,
                "avg_completion_rate": 0.0
            },
            "created_by": ObjectId(data["created_by"]) if data.get("created_by") else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = SectionModel.get_collection().insert_one(section)
        
        return {
            "message": "Section créée avec succès",
            "section_id": str(result.inserted_id)
        }
    
    @staticmethod
    def get_section_by_id(section_id):
        """
        Récupère une section par son ID.
        """
        section = SectionModel.get_collection().find_one({"_id": ObjectId(section_id)})
        if section:
            section["_id"] = str(section["_id"])
            section["church_id"] = str(section["church_id"])
            if section.get("created_by"):
                section["created_by"] = str(section["created_by"])
            if section.get("source_section_id"):
                section["source_section_id"] = str(section["source_section_id"])
        return section
    
    @staticmethod
    def get_all_sections_by_church(church_id, is_sequential=None):
        """
        Récupère toutes les sections d'une église donnée.
        """
        query = {"church_id": ObjectId(church_id)}
        
        if is_sequential is not None:
            query["is_sequential"] = is_sequential
        
        sections = SectionModel.get_collection().find(query).sort("order", 1)
        return list(sections)
    
    @staticmethod
    def get_public_sections(skip=0, limit=20):
        """
        Récupère les sections publiques (catalogue).
        """
        sections = SectionModel.get_collection().find({
            "$or": [
                {"is_public": True},
                {"is_template": True}
            ]
        }).skip(skip).limit(limit)
        return list(sections)
    
    @staticmethod
    def count_public_sections():
        """
        Compte le nombre de sections publiques.
        """
        return SectionModel.get_collection().count_documents({
            "$or": [
                {"is_public": True},
                {"is_template": True}
            ]
        })
    
    @staticmethod
    def update_section(section_id, data):
        """
        Met à jour les informations d'une section existante.
        """
        update_data = {k: data[k] for k in data if k in [
            "title", "description", "order", "is_sequential", "icon"
        ]}
        update_data["updated_at"] = datetime.utcnow()
        
        result = SectionModel.get_collection().update_one(
            {"_id": ObjectId(section_id)},
            {"$set": update_data}
        )
        
        return {
            "message": "Section mise à jour avec succès",
            "modified_count": result.modified_count
        }
    
    @staticmethod
    def delete_section(section_id):
        """
        Supprime une section par son ID.
        """
        result = SectionModel.get_collection().delete_one({"_id": ObjectId(section_id)})
        
        return {
            "message": "Section supprimée avec succès",
            "deleted_count": result.deleted_count
        }
    
    @staticmethod
    def update_stats(section_id, total_chapters, total_quiz, avg_completion_rate):
        """
        Met à jour les statistiques d'une section.
        """
        result = SectionModel.get_collection().update_one(
            {"_id": ObjectId(section_id)},
            {
                "$set": {
                    "stats.total_chapters": total_chapters,
                    "stats.total_quiz": total_quiz,
                    "stats.avg_completion_rate": avg_completion_rate,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def publish_section(section_id):
        """
        Rend une section publique.
        """
        result = SectionModel.get_collection().update_one(
            {"_id": ObjectId(section_id)},
            {"$set": {"is_public": True, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    @staticmethod
    def unpublish_section(section_id):
        """
        Rend une section privée.
        """
        result = SectionModel.get_collection().update_one(
            {"_id": ObjectId(section_id)},
            {"$set": {"is_public": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    @staticmethod
    def get_next_order(church_id):
        """
        Obtient le prochain numéro d'ordre pour une nouvelle section.
        """
        last_section = SectionModel.get_collection().find_one(
            {"church_id": ObjectId(church_id)},
            sort=[("order", -1)]
        )
        return (last_section["order"] + 1) if last_section else 1
    
    @staticmethod
    def count_chapters_by_section(section_id):
        """
        Compte le nombre de chapitres dans une section.
        """
        from models.chapter_model import ChapterModel
        return ChapterModel.get_collection().count_documents({
            "section_id": ObjectId(section_id)
        })