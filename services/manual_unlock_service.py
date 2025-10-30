# services/manual_unlock_service.py

from bson import ObjectId
from datetime import datetime
from models.manual_unlock_model import ManualUnlockModel
from models.user_model import UserModel
from models.chapter_model import ChapterModel
from models.section_model import SectionModel

def get_all_unlocks_service(church_id, filters=None):
    """
    Récupère tous les déblocages d'une église avec enrichissement des données.
    """
    unlocks = ManualUnlockModel.get_all_unlocks_by_church(church_id, filters)
    
    # Récupérer les IDs uniques pour optimiser les requêtes
    learner_ids = list(set(str(u["learner_id"]) for u in unlocks))
    leader_ids = list(set(str(u["unlocked_by"]) for u in unlocks))
    chapter_ids = list(set(str(u["chapter_id"]) for u in unlocks))
    
    # Récupérer les utilisateurs (apprenants et leaders)
    all_user_ids = list(set(learner_ids + leader_ids))
    users = list(UserModel.collection.find({
        "_id": {"$in": [ObjectId(uid) for uid in all_user_ids]}
    }))
    user_map = {str(user["_id"]): user for user in users}
    
    # Récupérer les chapitres
    chapters = list(ChapterModel.get_collection().find({
        "_id": {"$in": [ObjectId(cid) for cid in chapter_ids]}
    }))
    chapter_map = {str(chapter["_id"]): chapter for chapter in chapters}
    
    # Enrichir les déblocages
    result = []
    for unlock in unlocks:
        unlock["_id"] = str(unlock["_id"])
        unlock["church_id"] = str(unlock["church_id"])
        unlock["learner_id"] = str(unlock["learner_id"])
        unlock["chapter_id"] = str(unlock["chapter_id"])
        unlock["unlocked_by"] = str(unlock["unlocked_by"])
        
        # Ajouter les infos de l'apprenant
        learner = user_map.get(unlock["learner_id"])
        if learner:
            unlock["learner_name"] = learner.get("name", "")
            unlock["learner_first_name"] = learner.get("first_name", "")
            unlock["learner_email"] = learner.get("email", "")
        else:
            unlock["learner_name"] = "Inconnu"
            unlock["learner_first_name"] = ""
            unlock["learner_email"] = ""
        
        # Ajouter les infos du leader
        leader = user_map.get(unlock["unlocked_by"])
        if leader:
            unlock["leader_name"] = leader.get("name", "")
            unlock["leader_first_name"] = leader.get("first_name", "")
            unlock["leader_role"] = leader.get("role", "")
        else:
            unlock["leader_name"] = "Inconnu"
            unlock["leader_first_name"] = ""
            unlock["leader_role"] = ""
        
        # Ajouter les infos du chapitre
        chapter = chapter_map.get(unlock["chapter_id"])
        if chapter:
            unlock["chapter_title"] = chapter.get("title", "")
            unlock["chapter_order"] = chapter.get("order", 0)
            
            # Récupérer la section
            section = SectionModel.get_section_by_id(str(chapter["section_id"]))
            if section:
                unlock["section_title"] = section.get("title", "")
                unlock["section_id"] = str(chapter["section_id"])
        else:
            unlock["chapter_title"] = "Inconnu"
            unlock["chapter_order"] = 0
            unlock["section_title"] = ""
            unlock["section_id"] = ""
        
        result.append(unlock)
    
    return result


def get_unlocks_by_learner_service(learner_id, church_id):
    """
    Récupère tous les déblocages d'un apprenant avec enrichissement.
    """
    unlocks = ManualUnlockModel.get_unlocks_by_learner(learner_id, church_id)
    
    # Enrichir
    result = []
    for unlock in unlocks:
        unlock["_id"] = str(unlock["_id"])
        unlock["church_id"] = str(unlock["church_id"])
        unlock["learner_id"] = str(unlock["learner_id"])
        unlock["chapter_id"] = str(unlock["chapter_id"])
        unlock["unlocked_by"] = str(unlock["unlocked_by"])
        
        # Récupérer le leader
        leader = UserModel.collection.find_one({"_id": ObjectId(unlock["unlocked_by"])})
        if leader:
            unlock["leader_name"] = leader.get("name", "")
            unlock["leader_first_name"] = leader.get("first_name", "")
        
        # Récupérer le chapitre
        chapter = ChapterModel.get_chapter_by_id(unlock["chapter_id"])
        if chapter:
            unlock["chapter_title"] = chapter.get("title", "")
            unlock["section_id"] = chapter.get("section_id", "")
        
        result.append(unlock)
    
    return result


def get_unlocks_by_chapter_service(chapter_id, church_id):
    """
    Récupère tous les déblocages pour un chapitre avec enrichissement.
    """
    unlocks = ManualUnlockModel.get_unlocks_by_chapter(chapter_id, church_id)
    
    # Enrichir
    result = []
    for unlock in unlocks:
        unlock["_id"] = str(unlock["_id"])
        unlock["church_id"] = str(unlock["church_id"])
        unlock["learner_id"] = str(unlock["learner_id"])
        unlock["chapter_id"] = str(unlock["chapter_id"])
        unlock["unlocked_by"] = str(unlock["unlocked_by"])
        
        # Récupérer l'apprenant
        learner = UserModel.collection.find_one({"_id": ObjectId(unlock["learner_id"])})
        if learner:
            unlock["learner_name"] = learner.get("name", "")
            unlock["learner_first_name"] = learner.get("first_name", "")
            unlock["learner_email"] = learner.get("email", "")
        
        # Récupérer le leader
        leader = UserModel.collection.find_one({"_id": ObjectId(unlock["unlocked_by"])})
        if leader:
            unlock["leader_name"] = leader.get("name", "")
            unlock["leader_first_name"] = leader.get("first_name", "")
        
        result.append(unlock)
    
    return result


def get_unlock_stats_service(church_id):
    """
    Récupère les statistiques complètes des déblocages.
    """
    # Stats globales
    global_stats = ManualUnlockModel.get_unlock_stats_by_church(church_id)
    
    # Chapitres les plus débloqués
    most_unlocked_chapters = ManualUnlockModel.get_most_unlocked_chapters(church_id, 5)
    
    # Enrichir avec les titres des chapitres
    for item in most_unlocked_chapters:
        chapter = ChapterModel.get_chapter_by_id(str(item["chapter_id"]))
        if chapter:
            item["chapter_title"] = chapter.get("title", "")
            item["section_id"] = chapter.get("section_id", "")
        item["chapter_id"] = str(item["chapter_id"])
    
    # Leaders les plus actifs
    most_active_leaders = ManualUnlockModel.get_most_active_leaders(church_id, 5)
    
    # Enrichir avec les noms des leaders
    for item in most_active_leaders:
        leader = UserModel.collection.find_one({"_id": item["leader_id"]})
        if leader:
            item["leader_name"] = leader.get("name", "")
            item["leader_first_name"] = leader.get("first_name", "")
            item["leader_role"] = leader.get("role", "")
        item["leader_id"] = str(item["leader_id"])
    
    return {
        "global_stats": global_stats,
        "most_unlocked_chapters": most_unlocked_chapters,
        "most_active_leaders": most_active_leaders
    }


def delete_unlock_service(unlock_id, church_id):
    """
    Supprime un déblocage (pour correction d'erreurs).
    """
    unlock = ManualUnlockModel.get_unlock_by_id(unlock_id)
    
    if not unlock:
        return {"message": "Déblocage non trouvé"}, 404
    
    if unlock["church_id"] != str(church_id):
        return {"message": "Accès non autorisé"}, 403
    
    result = ManualUnlockModel.delete_unlock(unlock_id)
    return result, 200