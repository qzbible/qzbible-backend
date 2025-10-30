# models/chapter_model.py

from bson import ObjectId
from datetime import datetime
from extensions import mongo

class ChapterModel:
    
    collection = mongo.db.chapters
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.chapters
    
    @staticmethod
    def create_chapter(data):
        """
        Crée un nouveau chapitre avec les informations fournies.
        
        :param data: dict contenant les informations du chapitre
        :return: dict contenant le message de succès et l'ID du chapitre créé
        """
        chapter = {
            "section_id": ObjectId(data["section_id"]),
            "church_id": ObjectId(data["church_id"]),
            "title": data["title"],
            "description": data.get("description", ""),
            "order": data.get("order", 1),
            "content": data.get("content", {
                "introduction": None,
                "resources": []
            }),
            "unlock_requirements": data.get("unlock_requirements", {
                "previous_chapter_id": None,
                "min_score": 70,
                "completion_required": True
            }),
            "is_public": data.get("is_public", False),
            "source_chapter_id": ObjectId(data["source_chapter_id"]) if data.get("source_chapter_id") else None,
            "created_by": ObjectId(data["created_by"]) if data.get("created_by") else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Convertir previous_chapter_id en ObjectId si présent
        if chapter["unlock_requirements"].get("previous_chapter_id"):
            chapter["unlock_requirements"]["previous_chapter_id"] = ObjectId(
                chapter["unlock_requirements"]["previous_chapter_id"]
            )
        
        result = ChapterModel.get_collection().insert_one(chapter)
        
        return {
            "message": "Chapitre créé avec succès",
            "chapter_id": str(result.inserted_id)
        }
    
    @staticmethod
    def get_chapter_by_id(chapter_id):
        """
        Récupère un chapitre par son ID.
        """
        chapter = ChapterModel.get_collection().find_one({"_id": ObjectId(chapter_id)})
        if chapter:
            chapter["_id"] = str(chapter["_id"])
            chapter["section_id"] = str(chapter["section_id"])
            chapter["church_id"] = str(chapter["church_id"])
            
            if chapter.get("created_by"):
                chapter["created_by"] = str(chapter["created_by"])
            if chapter.get("source_chapter_id"):
                chapter["source_chapter_id"] = str(chapter["source_chapter_id"])
            
            # Convertir previous_chapter_id
            if chapter.get("unlock_requirements", {}).get("previous_chapter_id"):
                chapter["unlock_requirements"]["previous_chapter_id"] = str(
                    chapter["unlock_requirements"]["previous_chapter_id"]
                )
        
        return chapter
    
    @staticmethod
    def get_all_chapters_by_section(section_id):
        """
        Récupère tous les chapitres d'une section donnée.
        """
        chapters = ChapterModel.get_collection().find({
            "section_id": ObjectId(section_id)
        }).sort("order", 1)
        return list(chapters)
    
    @staticmethod
    def get_all_chapters_by_church(church_id):
        """
        Récupère tous les chapitres d'une église.
        """
        chapters = ChapterModel.get_collection().find({
            "church_id": ObjectId(church_id)
        }).sort("order", 1)
        return list(chapters)
    
    @staticmethod
    def update_chapter(chapter_id, data):
        """
        Met à jour les informations d'un chapitre existant.
        """
        update_data = {k: data[k] for k in data if k in [
            "title", "description", "order", "content", "unlock_requirements"
        ]}
        update_data["updated_at"] = datetime.utcnow()
        
        # Convertir previous_chapter_id si présent dans unlock_requirements
        if "unlock_requirements" in update_data:
            if update_data["unlock_requirements"].get("previous_chapter_id"):
                update_data["unlock_requirements"]["previous_chapter_id"] = ObjectId(
                    update_data["unlock_requirements"]["previous_chapter_id"]
                )
        
        result = ChapterModel.get_collection().update_one(
            {"_id": ObjectId(chapter_id)},
            {"$set": update_data}
        )
        
        return {
            "message": "Chapitre mis à jour avec succès",
            "modified_count": result.modified_count
        }
    
    @staticmethod
    def delete_chapter(chapter_id):
        """
        Supprime un chapitre par son ID.
        """
        result = ChapterModel.get_collection().delete_one({"_id": ObjectId(chapter_id)})
        
        return {
            "message": "Chapitre supprimé avec succès",
            "deleted_count": result.deleted_count
        }
    
    @staticmethod
    def count_by_section(section_id):
        """
        Compte le nombre de chapitres dans une section.
        """
        return ChapterModel.get_collection().count_documents({
            "section_id": ObjectId(section_id)
        })
    
    @staticmethod
    def get_next_order(section_id):
        """
        Obtient le prochain numéro d'ordre pour un nouveau chapitre.
        """
        last_chapter = ChapterModel.get_collection().find_one(
            {"section_id": ObjectId(section_id)},
            sort=[("order", -1)]
        )
        return (last_chapter["order"] + 1) if last_chapter else 1
    
    @staticmethod
    def get_first_chapter(section_id):
        """
        Récupère le premier chapitre d'une section.
        """
        chapter = ChapterModel.get_collection().find_one(
            {"section_id": ObjectId(section_id)},
            sort=[("order", 1)]
        )
        return chapter
    
    @staticmethod
    def get_previous_chapter(section_id, current_order):
        """
        Récupère le chapitre précédent dans une section.
        """
        chapter = ChapterModel.get_collection().find_one(
            {
                "section_id": ObjectId(section_id),
                "order": {"$lt": current_order}
            },
            sort=[("order", -1)]
        )
        return chapter
    
    @staticmethod
    def get_next_chapter(section_id, current_order):
        """
        Récupère le chapitre suivant dans une section.
        """
        chapter = ChapterModel.get_collection().find_one(
            {
                "section_id": ObjectId(section_id),
                "order": {"$gt": current_order}
            },
            sort=[("order", 1)]
        )
        return chapter
    
    @staticmethod
    def count_quiz_by_chapter(chapter_id):
        """
        Compte le nombre de quiz dans un chapitre.
        """
        from models.quiz_model import QuizModel
        return QuizModel.get_collection().count_documents({
            "chapter_id": ObjectId(chapter_id)
        })
    
    @staticmethod
    def publish_chapter(chapter_id):
        """
        Rend un chapitre public.
        """
        result = ChapterModel.get_collection().update_one(
            {"_id": ObjectId(chapter_id)},
            {"$set": {"is_public": True, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    @staticmethod
    def unpublish_chapter(chapter_id):
        """
        Rend un chapitre privé.
        """
        result = ChapterModel.get_collection().update_one(
            {"_id": ObjectId(chapter_id)},
            {"$set": {"is_public": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0