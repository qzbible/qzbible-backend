# services/user_progress_service.py

from bson import ObjectId
from models.user_progress_model import UserProgressModel
from models.section_model import SectionModel
from models.chapter_model import ChapterModel
from models.quiz_model import QuizModel
from models.user_model import UserModel
from datetime import datetime 


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
    


def get_current_section_service(user_id, church_id):
    """
    Récupère la section courante avec statistiques précises.
    
    Données globales (toutes sections) :
    - Nombre de quiz avec score parfait (100%)
    - Nombre total de quiz passés
    
    Données de la section courante :
    - Points totaux possibles (toutes questions de tous quiz)
    - Points obtenus (tous quiz passés)
    - Nombre de quiz passés
    - Nombre de jours depuis le début
    - Nombre de chapitres
    """
    progress = UserProgressModel.get_progress_by_user(user_id, church_id)
    
    # 🎯 CAS 1 : Aucune progression du tout - Initialiser la première section
    if not progress or not progress.get("sections_progress"):
        sections = SectionModel.get_all_sections_by_church(church_id)
        
        if not sections or len(sections) == 0:
            return {"message": "Aucune section disponible dans cette église"}, 404
        
        sections.sort(key=lambda x: x.get("order", 0))
        first_section = sections[0]
        
        chapters = ChapterModel.get_all_chapters_by_section(str(first_section["_id"]))
        chapters.sort(key=lambda x: x.get("order", 0))
        
        # Calculer les points totaux possibles de la section
        total_points_possible = 0
        total_quizzes_count = 0
        
        for chapter in chapters:
            quizzes = QuizModel.get_all_quizzes_by_chapter(str(chapter["_id"]))
            for quiz in quizzes:
                total_quizzes_count += 1
                # Calculer les points du quiz
                quiz_points = sum(q.get("points", 0) for q in quiz.get("questions", []))
                total_points_possible += quiz_points
        
        # Construire la réponse initiale
        result = {
            "global_stats": {
                "perfect_score_quizzes_count": 0,  # Aucun quiz passé
                "total_quizzes_passed": 0           # Aucun quiz passé
            },
            "section": {
                "_id": str(first_section["_id"]),
                "title": first_section.get("title"),
                "description": first_section.get("description"),
                "is_sequential": first_section.get("is_sequential"),
                "order": first_section.get("order")
            },
            "section_stats": {
                "total_points_possible": total_points_possible,
                "total_points_obtained": 0,
                "quizzes_passed_count": 0,
                "days_since_start": 0,
                "chapters_count": len(chapters)
            }
        }
        
        return result, 200
    
    # 🎯 CAS 2 : Progression existe
    sections_progress = progress.get("sections_progress", [])
    
    # Déterminer la section courante
    in_progress_sections = [s for s in sections_progress if s.get("status") == "in_progress"]
    
    if in_progress_sections:
        in_progress_sections.sort(key=lambda x: x.get("completion_percentage", 0), reverse=True)
        current_section_progress = in_progress_sections[0]
    else:
        completed_sections = [s for s in sections_progress if s.get("status") == "completed"]
        
        if completed_sections:
            completed_sections.sort(key=lambda x: x.get("completed_at") or datetime.min, reverse=True)
            current_section_progress = completed_sections[0]
        else:
            not_started_sections = [s for s in sections_progress if s.get("status") == "not_started"]
            
            if not_started_sections:
                current_section_progress = not_started_sections[0]
            else:
                return {"message": "Aucune section disponible"}, 404
    
    # Récupérer les infos de la section
    section = SectionModel.get_section_by_id(current_section_progress["section_id"])
    
    if not section:
        return {"message": "Section non trouvée"}, 404
    
    # 📊 STATISTIQUES GLOBALES (toutes sections confondues)
    perfect_score_count = 0
    total_quizzes_passed = 0
    
    for section_prog in sections_progress:
        for chapter_prog in section_prog.get("chapters_progress", []):
            for quiz_prog in chapter_prog.get("quizzes_progress", []):
                if quiz_prog.get("status") == "passed":
                    total_quizzes_passed += 1
                    
                    # Vérifier si score parfait (100%)
                    if quiz_prog.get("best_score", 0) >= 100:
                        perfect_score_count += 1
    
    # 📊 STATISTIQUES DE LA SECTION COURANTE
    chapters_progress = current_section_progress.get("chapters_progress", [])
    
    # a. Calculer la somme de tous les points possibles
    total_points_possible = 0
    
    for chapter_prog in chapters_progress:
        chapter_id = chapter_prog["chapter_id"]
        quizzes = QuizModel.get_all_quizzes_by_chapter(str(chapter_id))
        
        for quiz in quizzes:
            # Sommer tous les points de toutes les questions du quiz
            quiz_points = sum(q.get("points", 0) for q in quiz.get("questions", []))
            total_points_possible += quiz_points
    
    # b. Calculer la somme de tous les points obtenus
    total_points_obtained = 0
    
    for chapter_prog in chapters_progress:
        for quiz_prog in chapter_prog.get("quizzes_progress", []):
            if quiz_prog.get("status") == "passed":
                quiz_id = quiz_prog["quiz_id"]
                
                # Récupérer le quiz pour connaître le max de points
                quiz = QuizModel.get_quiz_by_id(str(quiz_id))
                if quiz:
                    max_points = sum(q.get("points", 0) for q in quiz.get("questions", []))
                    
                    # Calculer les points obtenus à partir du pourcentage
                    best_score_percentage = quiz_prog.get("best_score", 0)
                    points_obtained = (best_score_percentage / 100) * max_points
                    total_points_obtained += points_obtained
    
    # c. Nombre de quiz passés dans la section
    quizzes_passed_in_section = 0
    
    for chapter_prog in chapters_progress:
        for quiz_prog in chapter_prog.get("quizzes_progress", []):
            if quiz_prog.get("status") == "passed":
                quizzes_passed_in_section += 1
    
    # Calculer le nombre de jours depuis le début de la section
    started_at = current_section_progress.get("started_at")
    
    if started_at:
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        
        days_since_start = (datetime.utcnow() - started_at).days
    else:
        days_since_start = 0
    
    # Nombre de chapitres dans la section
    chapters_count = len(chapters_progress)
    
    # 🎯 CONSTRUIRE LA RÉPONSE FINALE
    result = {
        "global_stats": {
            "perfect_score_quizzes_count": perfect_score_count,
            "total_quizzes_passed": total_quizzes_passed
        },
        "section": {
            "_id": section["_id"],
            "title": section.get("title"),
            "description": section.get("description"),
            "is_sequential": section.get("is_sequential"),
            "order": section.get("order")
        },
        "section_stats": {
            "total_points_possible": round(total_points_possible, 2),
            "total_points_obtained": round(total_points_obtained, 2),
            "quizzes_passed_count": quizzes_passed_in_section,
            "days_since_start": days_since_start,
            "chapters_count": chapters_count
        }
    }
    
    return result, 200


def get_recommended_next_action_service(user_id, church_id):
    """
    Recommande la prochaine action à effectuer par l'utilisateur.
    """
    progress = UserProgressModel.get_progress_by_user(user_id, church_id)
    
    if not progress or not progress.get("sections_progress"):
        # Aucune progression, recommander de commencer
        from models.section_model import SectionModel
        sections = SectionModel.get_all_sections_by_church(church_id)
        
        if sections:
            first_section = sections[0]
            return {
                "action": "start_first_section",
                "message": "Commencez votre formation !",
                "section": {
                    "_id": str(first_section["_id"]),
                    "title": first_section.get("title"),
                    "description": first_section.get("description")
                }
            }, 200
        else:
            return {
                "action": "no_content",
                "message": "Aucun contenu disponible pour le moment"
            }, 200
    
    sections_progress = progress.get("sections_progress", [])
    
    # Chercher une section en cours
    for section_prog in sections_progress:
        if section_prog.get("status") == "in_progress":
            # Chercher le premier chapitre non complété
            for chapter_prog in section_prog.get("chapters_progress", []):
                if chapter_prog.get("is_unlocked") and chapter_prog.get("status") != "completed":
                    chapter = ChapterModel.get_chapter_by_id(chapter_prog["chapter_id"])
                    
                    # Chercher un quiz non passé dans ce chapitre
                    for quiz_prog in chapter_prog.get("quizzes_progress", []):
                        if quiz_prog.get("status") in ["not_attempted", "failed"]:
                            quiz = QuizModel.get_quiz_by_id(quiz_prog["quiz_id"])
                            
                            return {
                                "action": "take_quiz",
                                "message": f"Continuez avec le quiz : {quiz.get('title')}",
                                "chapter": {
                                    "_id": str(chapter["_id"]),
                                    "title": chapter.get("title")
                                },
                                "quiz": {
                                    "_id": str(quiz["_id"]),
                                    "title": quiz.get("title")
                                }
                            }, 200
                    
                    # Pas de quiz en attente, recommander de lire le chapitre
                    return {
                        "action": "read_chapter",
                        "message": f"Continuez avec le chapitre : {chapter.get('title')}",
                        "chapter": {
                            "_id": str(chapter["_id"]),
                            "title": chapter.get("title"),
                            "description": chapter.get("description")
                        }
                    }, 200
    
    # Aucune section en cours, chercher la première non commencée
    for section_prog in sections_progress:
        if section_prog.get("status") == "not_started":
            section = SectionModel.get_section_by_id(section_prog["section_id"])
            return {
                "action": "start_section",
                "message": f"Commencez la section : {section.get('title')}",
                "section": {
                    "_id": str(section["_id"]),
                    "title": section.get("title"),
                    "description": section.get("description")
                }
            }, 200
    
    # Tout est complété !
    return {
        "action": "all_completed",
        "message": "Félicitations ! Vous avez terminé toutes les sections disponibles 🎉",
        "overall_stats": progress.get("overall_stats")
    }, 200


# services/user_progress_service.py

def update_user_progress_after_quiz(user_id, quiz_id, chapter_id, church_id, score_percentage, passed):
    """
    Met à jour la progression de l'utilisateur après un quiz.
    """
    
    # 1. Récupérer ou créer la progression
    progress = UserProgressModel.get_or_create_progress(user_id, church_id)
    
     
    # 2. Récupérer le chapitre pour connaître sa section
    chapter = ChapterModel.get_chapter_by_id(chapter_id)
    if not chapter:
        return
    
    section_id = str(chapter["section_id"])
    
    # 3. Trouver ou créer la section dans la progression
    section_progress = None
    section_index = None
    
    for idx, sp in enumerate(progress.get("sections_progress", [])):
        if str(sp["section_id"]) == section_id:
            section_progress = sp
            section_index = idx
            break
    
    # 🎯 SI la section n'existe pas, la créer
    if not section_progress:
        section = SectionModel.get_section_by_id(section_id)
        if not section:
            return  # Section non trouvée
        
        # Créer la progression de la section
        section_progress = {
            "section_id": section_id,
            "status": "in_progress",
            "completion_percentage": 0,
            "started_at": datetime.utcnow(),
            "completed_at": None,
            "total_time_spent_seconds": 0,
            "chapters_progress": []
        }
        
        # Ajouter au tableau
        if "sections_progress" not in progress:
            progress["sections_progress"] = []
        
        progress["sections_progress"].append(section_progress)
        section_index = len(progress["sections_progress"]) - 1
    
    # 4. Trouver ou créer le chapitre dans la section
    chapter_progress = None
    chapter_index = None
    
    for idx, cp in enumerate(section_progress.get("chapters_progress", [])):
        if str(cp["chapter_id"]) == chapter_id:
            chapter_progress = cp
            chapter_index = idx
            break
    
    # 🎯 SI le chapitre n'existe pas, le créer
    if not chapter_progress:
        # Créer la progression du chapitre
        chapter_progress = {
            "chapter_id": chapter_id,
            "status": "in_progress",
            "is_unlocked": True,  # Si on peut passer le quiz, c'est qu'il est débloqué
            "unlocked_at": datetime.utcnow(),
            "unlocked_by": "auto",
            "completion_percentage": 0,
            "avg_score": 0,
            "started_at": datetime.utcnow(),
            "completed_at": None,
            "total_time_spent_seconds": 0,
            "quizzes_progress": []
        }
        
        # Ajouter au tableau
        section_progress["chapters_progress"].append(chapter_progress)
        chapter_index = len(section_progress["chapters_progress"]) - 1
    
    # 5. Trouver ou créer la progression du quiz
    quiz_progress = None
    quiz_index = None
    
    for idx, qp in enumerate(chapter_progress.get("quizzes_progress", [])):
        if str(qp["quiz_id"]) == quiz_id:
            quiz_progress = qp
            quiz_index = idx
            break
    
    # 🎯 SI le quiz n'existe pas, le créer
    if not quiz_progress:
        quiz_progress = {
            "quiz_id": quiz_id,
            "status": "not_attempted",
            "attempts_count": 0,
            "best_score": 0,
            "last_attempt_score": 0,
            "last_attempt_at": None
        }
        chapter_progress["quizzes_progress"].append(quiz_progress)
        quiz_index = len(chapter_progress["quizzes_progress"]) - 1
    
    # 6. 🎯 Mettre à jour la progression du quiz
    quiz_progress["attempts_count"] = quiz_progress.get("attempts_count", 0) + 1
    quiz_progress["last_attempt_score"] = score_percentage
    quiz_progress["last_attempt_at"] = datetime.utcnow()
    
    # Mettre à jour le meilleur score
    if score_percentage > quiz_progress.get("best_score", 0):
        quiz_progress["best_score"] = score_percentage
    
    # Mettre à jour le statut
    if passed:
        quiz_progress["status"] = "passed"
    elif quiz_progress.get("status") == "not_attempted":
        quiz_progress["status"] = "failed"
    
    # Mettre à jour dans chapter_progress
    chapter_progress["quizzes_progress"][quiz_index] = quiz_progress
    
    # 7. 🎯 Recalculer la progression du chapitre
    total_quizzes = len(chapter_progress["quizzes_progress"])
    passed_quizzes = len([q for q in chapter_progress["quizzes_progress"] if q.get("status") == "passed"])
    
    if total_quizzes > 0:
        chapter_progress["completion_percentage"] = (passed_quizzes / total_quizzes) * 100
        
        # Calculer le score moyen
        scores = [q["best_score"] for q in chapter_progress["quizzes_progress"] if q.get("best_score", 0) > 0]
        chapter_progress["avg_score"] = sum(scores) / len(scores) if scores else 0
    
    # Mettre à jour le statut du chapitre
    if passed_quizzes == total_quizzes and total_quizzes > 0:
        chapter_progress["status"] = "completed"
        if not chapter_progress.get("completed_at"):
            chapter_progress["completed_at"] = datetime.utcnow()
    elif passed_quizzes > 0:
        chapter_progress["status"] = "in_progress"
    
    # Mettre à jour dans section_progress
    section_progress["chapters_progress"][chapter_index] = chapter_progress
    
    # 8. 🎯 Vérifier déblocage du chapitre suivant
    if chapter_progress["status"] == "completed":
        next_chapter_index = chapter_index + 1
        
        if next_chapter_index < len(section_progress["chapters_progress"]):
            next_chapter_progress = section_progress["chapters_progress"][next_chapter_index]
            
            next_chapter_data = ChapterModel.get_chapter_by_id(str(next_chapter_progress["chapter_id"]))
            
            if next_chapter_data:
                unlock_conditions = next_chapter_data.get("unlock_conditions", {})
                min_score = unlock_conditions.get("min_score", 0)
                completion_required = unlock_conditions.get("completion_required", True)
                
                can_unlock = (
                    chapter_progress["avg_score"] >= min_score and
                    (not completion_required or chapter_progress["status"] == "completed")
                )
                
                if can_unlock and not next_chapter_progress.get("is_unlocked"):
                    next_chapter_progress["is_unlocked"] = True
                    next_chapter_progress["unlocked_at"] = datetime.utcnow()
                    next_chapter_progress["unlocked_by"] = "auto"
                    
                    section_progress["chapters_progress"][next_chapter_index] = next_chapter_progress
    
    # 9. 🎯 Recalculer la progression de la section
    total_chapters = len(section_progress["chapters_progress"])
    completed_chapters = len([c for c in section_progress["chapters_progress"] if c.get("status") == "completed"])
    
    if total_chapters > 0:
        section_progress["completion_percentage"] = (completed_chapters / total_chapters) * 100
    
    if completed_chapters == total_chapters and total_chapters > 0:
        section_progress["status"] = "completed"
        if not section_progress.get("completed_at"):
            section_progress["completed_at"] = datetime.utcnow()
    elif completed_chapters > 0:
        section_progress["status"] = "in_progress"
    
    # Mettre à jour dans progress
    progress["sections_progress"][section_index] = section_progress
    
    # 10. 🎯 Mettre à jour les statistiques globales
    overall_stats = progress.get("overall_stats", {})
    overall_stats["total_quiz_completed"] = overall_stats.get("total_quiz_completed", 0) + 1
    
    if passed:
        overall_stats["total_quiz_passed"] = overall_stats.get("total_quiz_passed", 0) + 1
    
    # Recalculer le score moyen global
    all_quiz_scores = []
    for sp in progress["sections_progress"]:
        for cp in sp.get("chapters_progress", []):
            for qp in cp.get("quizzes_progress", []):
                if qp.get("best_score", 0) > 0:
                    all_quiz_scores.append(qp["best_score"])
    
    if all_quiz_scores:
        overall_stats["avg_score"] = sum(all_quiz_scores) / len(all_quiz_scores)
    
    # Mettre à jour le streak
    today = datetime.utcnow().date()
    last_activity = progress.get("last_activity_date")
    
    if last_activity:
        last_date = last_activity.date() if isinstance(last_activity, datetime) else last_activity
        days_diff = (today - last_date).days
        
        if days_diff == 0:
            pass
        elif days_diff == 1:
            overall_stats["current_streak_days"] = overall_stats.get("current_streak_days", 0) + 1
            
            if overall_stats["current_streak_days"] > overall_stats.get("longest_streak_days", 0):
                overall_stats["longest_streak_days"] = overall_stats["current_streak_days"]
        else:
            overall_stats["current_streak_days"] = 1
    else:
        overall_stats["current_streak_days"] = 1
        overall_stats["longest_streak_days"] = 1
    
    progress["overall_stats"] = overall_stats
    progress["last_activity_date"] = datetime.utcnow()
    
    # 11. 🎯 Sauvegarder dans MongoDB
    UserProgressModel.get_collection().update_one(
        {"_id": ObjectId(progress["_id"])},
        {"$set": {
            "sections_progress": progress["sections_progress"],
            "overall_stats": progress["overall_stats"],
            "last_activity_date": progress["last_activity_date"],
            "updated_at": datetime.utcnow()
        }}
    )