# services/chapter_service.py

from bson import ObjectId
from models.chapter_model import ChapterModel
from models.section_model import SectionModel
from models.user_model import UserModel
import json

def create_chapter_service(data):
    """
    Crée un nouveau chapitre.
    """
    # Vérifier que la section existe
    section = SectionModel.get_section_by_id(data["section_id"])
    if not section:
        return {"message": "Section non trouvée"}, 404
    
    # Calculer l'ordre automatiquement si non fourni
    if not data.get("order"):
        data["order"] = ChapterModel.get_next_order(data["section_id"])
    
    # Si c'est le premier chapitre, pas de previous_chapter_id
    if data["order"] == 1:
        if "unlock_requirements" not in data:
            data["unlock_requirements"] = {}
        data["unlock_requirements"]["previous_chapter_id"] = None
    else:
        # Sinon, trouver le chapitre précédent
        previous_chapter = ChapterModel.get_previous_chapter(
            data["section_id"], 
            data["order"]
        )
        if previous_chapter and "unlock_requirements" in data:
            if not data["unlock_requirements"].get("previous_chapter_id"):
                data["unlock_requirements"]["previous_chapter_id"] = str(previous_chapter["_id"])
    
    result = ChapterModel.create_chapter(data)
    
    # Mettre à jour les stats de la section
    total_chapters = ChapterModel.count_by_section(data["section_id"])
    SectionModel.update_stats(
        data["section_id"],
        total_chapters=total_chapters,
        total_quiz=0,  # À calculer si nécessaire
        avg_completion_rate=0.0
    )
    
    return result, 201


def get_all_chapters_service(section_id):
    """
    Récupère tous les chapitres d'une section.
    """
    if isinstance(section_id, dict) and "$oid" in section_id:
        section_id = section_id["$oid"]
    
    chapters = ChapterModel.get_all_chapters_by_section(section_id)
    
    for chapter in chapters:
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
    
    return chapters


def get_chapter_by_id_service(chapter_id):
    """
    Récupère un chapitre par son ID.
    """
    chapter = ChapterModel.get_chapter_by_id(chapter_id)
    return chapter


def update_chapter_service(chapter_id, data):
    """
    Met à jour un chapitre.
    """
    return ChapterModel.update_chapter(chapter_id, data)


def delete_chapter_service(chapter_id):
    """
    Supprime un chapitre.
    """
    # Vérifier s'il y a des quiz associés
    quiz_count = ChapterModel.count_quiz_by_chapter(chapter_id)
    if quiz_count > 0:
        return {
            "message": f"Impossible de supprimer ce chapitre. Il contient {quiz_count} quiz.",
            "quiz_count": quiz_count
        }, 400
    
    # Récupérer le chapitre avant suppression pour mettre à jour les stats
    chapter = ChapterModel.get_chapter_by_id(chapter_id)
    section_id = chapter["section_id"]
    
    result = ChapterModel.delete_chapter(chapter_id)
    
    # Mettre à jour les stats de la section
    total_chapters = ChapterModel.count_by_section(section_id)
    SectionModel.update_stats(
        section_id,
        total_chapters=total_chapters,
        total_quiz=0,
        avg_completion_rate=0.0
    )
    
    return result, 200


def get_chapters_with_creator_info(section_id):
    """
    Récupère les chapitres avec les infos des créateurs.
    """
    chapters = ChapterModel.get_all_chapters_by_section(section_id)
    
    # Récupérer les IDs des créateurs
    creator_ids = list({
        str(chapter.get("created_by"))
        for chapter in chapters
        if chapter.get("created_by") is not None
    })
    
    # Récupérer les infos des utilisateurs
    users = UserModel.collection.find(
        {"_id": {"$in": [ObjectId(uid) for uid in creator_ids]}}
    )
    user_map = {str(user["_id"]): user for user in users}
    
    # Enrichir les chapitres
    result = []
    for chapter in chapters:
        chapter["_id"] = str(chapter["_id"])
        chapter["section_id"] = str(chapter["section_id"])
        chapter["church_id"] = str(chapter["church_id"])
        
        creator_id = str(chapter.get("created_by", ""))
        if creator_id and creator_id in user_map:
            chapter["created_by_name"] = user_map[creator_id].get("name", "")
            chapter["created_by_first_name"] = user_map[creator_id].get("first_name", "")
        else:
            chapter["created_by_name"] = ""
            chapter["created_by_first_name"] = ""
        
        if chapter.get("source_chapter_id"):
            chapter["source_chapter_id"] = str(chapter["source_chapter_id"])
        
        # Convertir previous_chapter_id
        if chapter.get("unlock_requirements", {}).get("previous_chapter_id"):
            chapter["unlock_requirements"]["previous_chapter_id"] = str(
                chapter["unlock_requirements"]["previous_chapter_id"]
            )
        
        result.append(chapter)
    
    return result


def clone_chapter_service(chapter_id, new_section_id, new_church_id, cloned_by):
    """
    Clone un chapitre vers une nouvelle section.
    """
    original_chapter = ChapterModel.get_chapter_by_id(chapter_id)
    
    if not original_chapter:
        return {"message": "Chapitre non trouvé"}, 404
    
    # Créer le nouveau chapitre
    cloned_data = {
        "section_id": new_section_id,
        "church_id": new_church_id,
        "title": original_chapter["title"],
        "description": original_chapter.get("description", ""),
        "order": ChapterModel.get_next_order(new_section_id),
        "content": original_chapter.get("content", {}),
        "unlock_requirements": original_chapter.get("unlock_requirements", {}),
        "is_public": False,
        "source_chapter_id": chapter_id,
        "created_by": cloned_by
    }
    
    # Réinitialiser previous_chapter_id pour le nouveau contexte
    if "unlock_requirements" in cloned_data:
        cloned_data["unlock_requirements"]["previous_chapter_id"] = None
    
    result = ChapterModel.create_chapter(cloned_data)
    
    return {
        "message": "Chapitre cloné avec succès",
        "chapter_id": result["chapter_id"]
    }, 201