# services/user_progress_service.py

from bson import ObjectId
from models.user_progress_model import UserProgressModel
from models.section_model import SectionModel
from models.chapter_model import ChapterModel
from models.quiz_model import QuizModel
from models.user_model import UserModel

def get_user_progress_service(user_id, church_id):
    """
    Récupère la progression complète d'un utilisateur.
    """
    progress = UserProgressModel.get_progress_by_user(user_id, church_id)
    
    if not progress:
        # Créer une progression vide
        progress = UserProgressModel.get_or_create_progress(user_id, church_id)
        progress = UserProgressModel.get_progress_by_user(user_id, church_id)
    
    return progress


def get_section_progress_service(user_id, church_id, section_id):
    """
    Récupère la progression d'un utilisateur pour une section spécifique.
    """
    progress = UserProgressModel.get_progress_by_user(user_id, church_id)
    
    if not progress:
        return {"message": "Progression non trouvée"}, 404
    
    # Trouver la progression de la section
    section_prog = None
    for sp in progress.get("sections_progress", []):
        if sp["section_id"] == str(section_id):
            section_prog = sp
            break
    
    if not section_prog:
        # Initialiser la section
        UserProgressModel.initialize_section_progress(user_id, church_id, section_id)
        progress = UserProgressModel.get_progress_by_user(user_id, church_id)
        for sp in progress.get("sections_progress", []):
            if sp["section_id"] == str(section_id):
                section_prog = sp
                break
    
    # Enrichir avec les infos de la section
    section = SectionModel.get_section_by_id(section_id)
    if section:
        section_prog["section_info"] = {
            "title": section.get("title"),
            "description": section.get("description"),
            "is_sequential": section.get("is_sequential")
        }
    
    return section_prog


def get_chapter_progress_service(user_id, church_id, chapter_id):
    """
    Récupère la progression d'un utilisateur pour un chapitre spécifique.
    """
    # Récupérer le chapitre pour trouver la section
    chapter = ChapterModel.get_chapter_by_id(chapter_id)
    if not chapter:
        return {"message": "Chapitre non trouvé"}, 404
    
    section_id = chapter["section_id"]
    
    progress = UserProgressModel.get_progress_by_user(user_id, church_id)
    
    if not progress:
        return {"message": "Progression non trouvée"}, 404
    
    # Trouver la progression du chapitre
    chapter_prog = None
    for sp in progress.get("sections_progress", []):
        if sp["section_id"] == str(section_id):
            for cp in sp.get("chapters_progress", []):
                if cp["chapter_id"] == str(chapter_id):
                    chapter_prog = cp
                    break
            break
    
    if not chapter_prog:
        # Initialiser la section si nécessaire
        UserProgressModel.initialize_section_progress(user_id, church_id, section_id)
        progress = UserProgressModel.get_progress_by_user(user_id, church_id)
        for sp in progress.get("sections_progress", []):
            if sp["section_id"] == str(section_id):
                for cp in sp.get("chapters_progress", []):
                    if cp["chapter_id"] == str(chapter_id):
                        chapter_prog = cp
                        break
                break
    
    # Enrichir avec les infos du chapitre
    chapter_prog["chapter_info"] = {
        "title": chapter.get("title"),
        "description": chapter.get("description"),
        "order": chapter.get("order")
    }
    
    return chapter_prog


def manual_unlock_chapter_service(admin_id, user_id, church_id, chapter_id, reason=None):
    """
    Débloque manuellement un chapitre pour un utilisateur.
    """
    # Récupérer le chapitre
    chapter = ChapterModel.get_chapter_by_id(chapter_id)
    if not chapter:
        return {"message": "Chapitre non trouvé"}, 404
    
    section_id = chapter["section_id"]
    
    # Débloquer le chapitre
    success = UserProgressModel.unlock_chapter(
        user_id, 
        church_id, 
        section_id, 
        chapter_id, 
        f"manual:{admin_id}"
    )
    
    if not success:
        return {"message": "Impossible de débloquer le chapitre"}, 500
    
    # Enregistrer dans manual_unlocks pour audit
    from extensions import mongo
    mongo.db.manual_unlocks.insert_one({
        "church_id": ObjectId(church_id),
        "learner_id": ObjectId(user_id),
        "chapter_id": ObjectId(chapter_id),
        "unlocked_by": ObjectId(admin_id),
        "reason": reason or "Déblocage manuel",
        "created_at": datetime.utcnow()
    })
    
    return {
        "message": "Chapitre débloqué avec succès",
        "chapter_id": chapter_id,
        "user_id": user_id
    }, 200


def get_learners_progress_service(church_id, section_id=None):
    """
    Récupère la progression de tous les apprenants d'une église.
    """
    query = {"church_id": ObjectId(church_id)}
    
    progressions = list(UserProgressModel.get_collection().find(query))
    
    result = []
    for prog in progressions:
        # Récupérer les infos de l'utilisateur
        user = UserModel.collection.find_one({"_id": prog["user_id"]})
        
        if not user:
            continue
        
        user_data = {
            "user_id": str(prog["user_id"]),
            "name": user.get("name", ""),
            "first_name": user.get("first_name", ""),
            "email": user.get("email", ""),
            "overall_stats": prog.get("overall_stats", {}),
            "sections_progress": []
        }
        
        # Filtrer par section si spécifié
        if section_id:
            for sp in prog.get("sections_progress", []):
                if str(sp["section_id"]) == str(section_id):
                    sp["section_id"] = str(sp["section_id"])
                    
                    # Convertir les ObjectId
                    for cp in sp.get("chapters_progress", []):
                        cp["chapter_id"] = str(cp["chapter_id"])
                        for qp in cp.get("quizzes_progress", []):
                            qp["quiz_id"] = str(qp["quiz_id"])
                            if qp.get("best_attempt_id"):
                                qp["best_attempt_id"] = str(qp["best_attempt_id"])
                    
                    user_data["sections_progress"].append(sp)
        else:
            # Convertir tous les ObjectId
            for sp in prog.get("sections_progress", []):
                sp["section_id"] = str(sp["section_id"])
                
                for cp in sp.get("chapters_progress", []):
                    cp["chapter_id"] = str(cp["chapter_id"])
                    for qp in cp.get("quizzes_progress", []):
                        qp["quiz_id"] = str(qp["quiz_id"])
                        if qp.get("best_attempt_id"):
                            qp["best_attempt_id"] = str(qp["best_attempt_id"])
                
                user_data["sections_progress"].append(sp)
        
        result.append(user_data)
    
    return result


def get_dashboard_stats_service(user_id, church_id):
    """
    Récupère les statistiques du dashboard pour un utilisateur.
    """
    progress = UserProgressModel.get_progress_by_user(user_id, church_id)
    
    if not progress:
        progress = UserProgressModel.get_or_create_progress(user_id, church_id)
        progress = UserProgressModel.get_progress_by_user(user_id, church_id)
    
    overall_stats = progress.get("overall_stats", {})
    
    # Calculer les sections complétées
    sections_progress = progress.get("sections_progress", [])
    total_sections = len(sections_progress)
    completed_sections = len([s for s in sections_progress if s.get("status") == "completed"])
    
    # Calculer les chapitres débloqués et complétés
    total_chapters = 0
    unlocked_chapters = 0
    completed_chapters = 0
    
    for sp in sections_progress:
        chapters = sp.get("chapters_progress", [])
        total_chapters += len(chapters)
        unlocked_chapters += len([c for c in chapters if c.get("is_unlocked")])
        completed_chapters += len([c for c in chapters if c.get("status") == "completed"])
    
    # Récupérer les tentatives récentes
    from models.quiz_attempt_model import QuizAttemptModel
    recent_attempts = list(QuizAttemptModel.get_collection().find({
        "user_id": ObjectId(user_id),
        "church_id": ObjectId(church_id),
        "status": "completed"
    }).sort("submitted_at", -1).limit(5))
    
    # Convertir les ObjectId
    for attempt in recent_attempts:
        attempt["_id"] = str(attempt["_id"])
        attempt["quiz_id"] = str(attempt["quiz_id"])
        attempt["user_id"] = str(attempt["user_id"])
        attempt["church_id"] = str(attempt["church_id"])
    
    dashboard = {
        "overall_stats": overall_stats,
        "sections": {
            "total": total_sections,
            "completed": completed_sections,
            "completion_rate": round((completed_sections / total_sections * 100), 2) if total_sections > 0 else 0
        },
        "chapters": {
            "total": total_chapters,
            "unlocked": unlocked_chapters,
            "completed": completed_chapters,
            "completion_rate": round((completed_chapters / total_chapters * 100), 2) if total_chapters > 0 else 0
        },
        "recent_attempts": recent_attempts
    }
    
    return dashboard


def get_leaderboard_service(church_id, section_id=None, limit=10):
    """
    Récupère le classement des apprenants.
    """
    query = {"church_id": ObjectId(church_id)}
    
    progressions = list(UserProgressModel.get_collection().find(query))
    
    leaderboard = []
    
    for prog in progressions:
        user = UserModel.collection.find_one({"_id": prog["user_id"]})
        
        if not user:
            continue
        
        overall_stats = prog.get("overall_stats", {})
        
        # Si filtré par section, calculer les stats de la section
        if section_id:
            section_stats = None
            for sp in prog.get("sections_progress", []):
                if str(sp["section_id"]) == str(section_id):
                    section_stats = {
                        "completion_percentage": sp.get("completion_percentage", 0),
                        "total_time_spent_seconds": sp.get("total_time_spent_seconds", 0)
                    }
                    break
            
            if not section_stats:
                continue
            
            leaderboard.append({
                "user_id": str(prog["user_id"]),
                "name": user.get("name", ""),
                "first_name": user.get("first_name", ""),
                "completion_percentage": section_stats["completion_percentage"],
                "total_time_spent_seconds": section_stats["total_time_spent_seconds"]
            })
        else:
            leaderboard.append({
                "user_id": str(prog["user_id"]),
                "name": user.get("name", ""),
                "first_name": user.get("first_name", ""),
                "total_quiz_completed": overall_stats.get("total_quiz_completed", 0),
                "total_quiz_passed": overall_stats.get("total_quiz_passed", 0),
                "avg_score": overall_stats.get("avg_score", 0),
                "current_streak_days": overall_stats.get("current_streak_days", 0)
            })
    
    # Trier par score moyen (ou completion_percentage pour section spécifique)
    if section_id:
        leaderboard.sort(key=lambda x: x["completion_percentage"], reverse=True)
    else:
        leaderboard.sort(key=lambda x: x["avg_score"], reverse=True)
    
    return leaderboard[:limit]


def reset_user_progress_service(user_id, church_id, section_id=None):
    """
    Réinitialise la progression d'un utilisateur (admin uniquement).
    """
    if section_id:
        # Réinitialiser uniquement une section
        progress = UserProgressModel.get_progress_by_user(user_id, church_id)
        
        if not progress:
            return {"message": "Progression non trouvée"}, 404
        
        # Supprimer la progression de la section
        UserProgressModel.get_collection().update_one(
            {
                "user_id": ObjectId(user_id),
                "church_id": ObjectId(church_id)
            },
            {
                "$pull": {
                    "sections_progress": {"section_id": ObjectId(section_id)}
                }
            }
        )
        
        return {"message": f"Progression de la section réinitialisée"}, 200
    else:
        # Réinitialiser toute la progression
        UserProgressModel.get_collection().delete_one({
            "user_id": ObjectId(user_id),
            "church_id": ObjectId(church_id)
        })
        
        return {"message": "Progression complète réinitialisée"}, 200