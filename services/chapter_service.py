# services/chapter_service.py

from bson import ObjectId
from models.chapter_model import ChapterModel
from models.quiz_model import QuizModel
from models.section_model import SectionModel
from models.user_model import UserModel
import json
from models.user_progress_model import UserProgressModel

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



def get_chapters_with_progress_service(section_id, user_id, church_id):
    """
    Récupère tous les chapitres d'une section avec la progression de l'utilisateur.
    
    Marque chaque chapitre comme :
    - not_started : Pas encore commencé
    - in_progress : En cours (au moins 1 quiz tenté, pas tous complétés)
    - completed : Terminé (tous les quiz réussis)
    
    Ajoute également l'ID du prochain quiz à faire ou du quiz en cours.
    
    🎯 NOUVELLE CONTRAINTE :
    Si aucun chapitre n'est en cours dans la section, démarre automatiquement
    le premier chapitre et retourne l'ID de son premier quiz.
    """ 
    
    # 1. Récupérer tous les chapitres de la section
    chapters = ChapterModel.get_all_chapters_by_section(section_id)
    chapters.sort(key=lambda x: x.get("order", 0))
    
    if not chapters:
        return {
            "chapters": [],
            "stats": {
                "total_chapters": 0,
                "completed_chapters": 0,
                "in_progress_chapters": 0,
                "not_started_chapters": 0,
                "overall_completion": 0
            },
            "recommended_action": None
        }
    
    # 2. Récupérer la progression de l'utilisateur
    progress = UserProgressModel.get_progress_by_user(user_id, church_id)
    
    # 3. Créer un map de progression par chapitre
    chapter_progress_map = {}
    section_has_progress = False
    
    if progress and progress.get("sections_progress"):
        for section_prog in progress["sections_progress"]:
            if str(section_prog["section_id"]) == str(section_id):
                section_has_progress = True
                for chapter_prog in section_prog.get("chapters_progress", []):
                    chapter_progress_map[str(chapter_prog["chapter_id"])] = chapter_prog
                break
    
    # 🎯 VÉRIFICATION : Aucun chapitre en cours dans cette section
    has_in_progress_chapter = any(
        cp.get("status") == "in_progress" 
        for cp in chapter_progress_map.values()
    )
    
    # 4. Enrichir chaque chapitre avec sa progression
    enriched_chapters = []
    stats = {
        "total_chapters": len(chapters),
        "completed_chapters": 0,
        "in_progress_chapters": 0,
        "not_started_chapters": 0,
        "overall_completion": 0
    }
    
    recommended_action = None
    
    for idx, chapter in enumerate(chapters):
        chapter_id = str(chapter["_id"])
        
        # Convertir les ObjectId en string
        chapter["_id"] = chapter_id
        chapter["section_id"] = str(chapter["section_id"])
        
        # Récupérer tous les quiz de ce chapitre
        quizzes = QuizModel.get_all_quizzes_by_chapter(chapter_id)
        quizzes.sort(key=lambda x: x.get("order", 0))
        
        # Récupérer la progression de ce chapitre
        chapter_prog = chapter_progress_map.get(chapter_id)
        
        if chapter_prog:
            # Chapitre avec progression
            status = chapter_prog.get("status", "not_started")
            
            # 🎯 Déterminer le prochain quiz ou quiz en cours
            next_quiz_id = None
            current_quiz_id = None
            
            quizzes_progress = chapter_prog.get("quizzes_progress", [])
            quiz_progress_map = {str(qp["quiz_id"]): qp for qp in quizzes_progress}
            
            for quiz in quizzes:
                quiz_id = str(quiz["_id"])
                quiz_prog = quiz_progress_map.get(quiz_id)
                
                if not quiz_prog or quiz_prog.get("status") == "not_attempted":
                    # Premier quiz non tenté = prochain quiz
                    next_quiz_id = quiz_id
                    break
                elif quiz_prog.get("status") == "failed":
                    # Quiz échoué = quiz actuel à refaire
                    current_quiz_id = quiz_id
                    next_quiz_id = quiz_id
                    break
                # Si "passed", continuer vers le suivant
            
            progress_info = {
                "status": status,
                "is_unlocked": chapter_prog.get("is_unlocked", False),
                "completion_percentage": round(chapter_prog.get("completion_percentage", 0), 2),
                "avg_score": round(chapter_prog.get("avg_score", 0), 2),
                "quizzes_total": len(quizzes),
                "quizzes_passed": len([
                    q for q in quizzes_progress 
                    if q.get("status") == "passed"
                ]),
                "started_at": chapter_prog.get("started_at"),
                "completed_at": chapter_prog.get("completed_at"),
                "next_quiz_id": next_quiz_id,
                "current_quiz_id": current_quiz_id
            }
            
            # Mettre à jour les stats
            if status == "completed":
                stats["completed_chapters"] += 1
            elif status == "in_progress":
                stats["in_progress_chapters"] += 1
            else:
                stats["not_started_chapters"] += 1
            
        else:
            # Chapitre sans progression (pas encore commencé)
            # Le premier quiz est le prochain
            next_quiz_id = str(quizzes[0]["_id"]) if quizzes else None
            
            # 🎯 Si c'est le premier chapitre ET qu'aucun chapitre n'est en cours
            is_unlocked = False
            if idx == 0 and not has_in_progress_chapter:
                is_unlocked = True
                
                # Créer une recommandation d'action
                if next_quiz_id:
                    recommended_action = {
                        "action": "start_first_chapter",
                        "message": f"Commencez votre formation avec le chapitre : {chapter.get('title')}",
                        "chapter_id": chapter_id,
                        "chapter_title": chapter.get("title"),
                        "quiz_id": next_quiz_id
                    }
            
            progress_info = {
                "status": "not_started",
                "is_unlocked": is_unlocked,
                "completion_percentage": 0,
                "avg_score": 0,
                "quizzes_total": len(quizzes),
                "quizzes_passed": 0,
                "started_at": None,
                "completed_at": None,
                "next_quiz_id": next_quiz_id,
                "current_quiz_id": None
            }
            stats["not_started_chapters"] += 1
        
        # Ajouter la progression au chapitre
        chapter["progress"] = progress_info
        enriched_chapters.append(chapter)
    
    # 🎯 Si aucune action recommandée et qu'il y a des chapitres en cours
    if not recommended_action and has_in_progress_chapter:
        # Trouver le premier chapitre en cours
        for chapter in enriched_chapters:
            if chapter["progress"]["status"] == "in_progress":
                quiz_id = chapter["progress"].get("current_quiz_id") or chapter["progress"].get("next_quiz_id")
                if quiz_id:
                    recommended_action = {
                        "action": "continue_chapter",
                        "message": f"Continuez avec le chapitre : {chapter.get('title')}",
                        "chapter_id": chapter["_id"],
                        "chapter_title": chapter.get("title"),
                        "quiz_id": quiz_id
                    }
                    break
    
    # Calculer la complétion globale
    if stats["total_chapters"] > 0:
        stats["overall_completion"] = round(
            (stats["completed_chapters"] / stats["total_chapters"]) * 100, 
            2
        )
    
    return {
        "chapters": enriched_chapters,
        "stats": stats,
        "recommended_action": recommended_action
    }