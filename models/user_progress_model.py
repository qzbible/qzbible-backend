# models/user_progress_model.py

from bson import ObjectId
from datetime import datetime, timedelta
from extensions import mongo

class UserProgressModel:
    
    collection = mongo.db.user_progress
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.user_progress
    
    @staticmethod
    def get_or_create_progress(user_id, church_id):
        """
        Récupère ou crée la progression d'un utilisateur.
        """
        progress = UserProgressModel.get_collection().find_one({
            "user_id": ObjectId(user_id),
            "church_id": ObjectId(church_id)
        })
        
        if not progress:
            # Créer une nouvelle progression
            progress = {
                "user_id": ObjectId(user_id),
                "church_id": ObjectId(church_id),
                "sections_progress": [],
                "overall_stats": {
                    "total_quiz_completed": 0,
                    "total_quiz_passed": 0,
                    "avg_score": 0.0,
                    "total_time_spent_seconds": 0,
                    "current_streak_days": 0,
                    "longest_streak_days": 0
                },
                "updated_at": datetime.utcnow()
            }
            
            result = UserProgressModel.get_collection().insert_one(progress)
            progress["_id"] = result.inserted_id
        
        return progress
    
    @staticmethod
    def get_progress_by_user(user_id, church_id):
        """
        Récupère la progression d'un utilisateur.
        """
        progress = UserProgressModel.get_collection().find_one({
            "user_id": ObjectId(user_id),
            "church_id": ObjectId(church_id)
        })
        
        if progress:
            progress["_id"] = str(progress["_id"])
            progress["user_id"] = str(progress["user_id"])
            progress["church_id"] = str(progress["church_id"])
            
            # Convertir les ObjectId dans sections_progress
            for section_prog in progress.get("sections_progress", []):
                section_prog["section_id"] = str(section_prog["section_id"])
                
                for chapter_prog in section_prog.get("chapters_progress", []):
                    chapter_prog["chapter_id"] = str(chapter_prog["chapter_id"])
                    
                    for quiz_prog in chapter_prog.get("quizzes_progress", []):
                        quiz_prog["quiz_id"] = str(quiz_prog["quiz_id"])
                        if quiz_prog.get("best_attempt_id"):
                            quiz_prog["best_attempt_id"] = str(quiz_prog["best_attempt_id"])
        
        return progress
    
    @staticmethod
    def initialize_section_progress(user_id, church_id, section_id):
        """
        Initialise la progression pour une nouvelle section.
        """
        from models.chapter_model import ChapterModel
        
        # Récupérer tous les chapitres de la section
        chapters = ChapterModel.get_all_chapters_by_section(section_id)
        
        chapters_progress = []
        for i, chapter in enumerate(chapters):
            # Le premier chapitre est débloqué par défaut
            is_unlocked = (i == 0)
            
            chapter_prog = {
                "chapter_id": chapter["_id"],
                "status": "not_started",
                "is_unlocked": is_unlocked,
                "unlocked_at": datetime.utcnow() if is_unlocked else None,
                "unlocked_by": "auto" if is_unlocked else None,
                "quizzes_progress": [],
                "completion_percentage": 0,
                "avg_score": 0
            }
            chapters_progress.append(chapter_prog)
        
        section_progress = {
            "section_id": ObjectId(section_id),
            "status": "not_started",
            "started_at": None,
            "completed_at": None,
            "chapters_progress": chapters_progress,
            "completion_percentage": 0,
            "total_time_spent_seconds": 0
        }
        
        # Ajouter à la progression de l'utilisateur
        UserProgressModel.get_collection().update_one(
            {
                "user_id": ObjectId(user_id),
                "church_id": ObjectId(church_id)
            },
            {
                "$push": {"sections_progress": section_progress},
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=True
        )
        
        return section_progress
    
    @staticmethod
    def update_quiz_progress(user_id, church_id, quiz_id, attempt_data):
        """
        Met à jour la progression d'un quiz après une tentative.
        """
        from models.quiz_model import QuizModel
        from models.chapter_model import ChapterModel
        from models.section_model import SectionModel
        
        # Récupérer le quiz pour trouver le chapitre et la section
        quiz = QuizModel.get_quiz_by_id(quiz_id)
        if not quiz:
            return False
        
        chapter_id = quiz["chapter_id"]
        chapter = ChapterModel.get_chapter_by_id(chapter_id)
        if not chapter:
            return False
        
        section_id = chapter["section_id"]
        
        # Récupérer la progression
        progress = UserProgressModel.get_or_create_progress(user_id, church_id)
        
        # Trouver ou créer la progression de la section
        section_prog = None
        section_idx = None
        for i, sp in enumerate(progress.get("sections_progress", [])):
            if str(sp["section_id"]) == str(section_id):
                section_prog = sp
                section_idx = i
                break
        
        if not section_prog:
            # Initialiser la section si elle n'existe pas
            UserProgressModel.initialize_section_progress(user_id, church_id, section_id)
            progress = UserProgressModel.get_or_create_progress(user_id, church_id)
            for i, sp in enumerate(progress.get("sections_progress", [])):
                if str(sp["section_id"]) == str(section_id):
                    section_prog = sp
                    section_idx = i
                    break
        
        # Trouver la progression du chapitre
        chapter_prog = None
        chapter_idx = None
        for i, cp in enumerate(section_prog.get("chapters_progress", [])):
            if str(cp["chapter_id"]) == str(chapter_id):
                chapter_prog = cp
                chapter_idx = i
                break
        
        if not chapter_prog:
            return False
        
        # Trouver ou créer la progression du quiz
        quiz_prog = None
        quiz_idx = None
        for i, qp in enumerate(chapter_prog.get("quizzes_progress", [])):
            if str(qp["quiz_id"]) == str(quiz_id):
                quiz_prog = qp
                quiz_idx = i
                break
        
        if not quiz_prog:
            # Créer une nouvelle progression de quiz
            quiz_prog = {
                "quiz_id": ObjectId(quiz_id),
                "attempts_count": 0,
                "best_score": 0,
                "best_attempt_id": None,
                "last_attempt_at": None,
                "status": "not_attempted"
            }
            chapter_prog["quizzes_progress"].append(quiz_prog)
            quiz_idx = len(chapter_prog["quizzes_progress"]) - 1
        
        # Mettre à jour la progression du quiz
        quiz_prog["attempts_count"] += 1
        quiz_prog["last_attempt_at"] = datetime.utcnow()
        
        if attempt_data["score"] > quiz_prog["best_score"]:
            quiz_prog["best_score"] = attempt_data["score"]
            quiz_prog["best_attempt_id"] = ObjectId(attempt_data["attempt_id"])
        
        if attempt_data["passed"]:
            quiz_prog["status"] = "passed"
        elif quiz_prog["status"] == "not_attempted":
            quiz_prog["status"] = "failed"
        
        # Mettre à jour dans la base de données
        update_path = f"sections_progress.{section_idx}.chapters_progress.{chapter_idx}.quizzes_progress.{quiz_idx}"
        
        UserProgressModel.get_collection().update_one(
            {
                "user_id": ObjectId(user_id),
                "church_id": ObjectId(church_id)
            },
            {
                "$set": {
                    update_path: quiz_prog,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Recalculer les pourcentages de progression
        UserProgressModel.recalculate_chapter_progress(user_id, church_id, section_id, chapter_id)
        
        # Vérifier le déblocage automatique du chapitre suivant
        UserProgressModel.check_auto_unlock(user_id, church_id, section_id, chapter_id)
        
        return True
    
    @staticmethod
    def recalculate_chapter_progress(user_id, church_id, section_id, chapter_id):
        """
        Recalcule la progression d'un chapitre.
        """
        from models.quiz_model import QuizModel
        
        progress = UserProgressModel.get_or_create_progress(user_id, church_id)
        
        # Trouver la section et le chapitre
        section_idx = None
        chapter_idx = None
        chapter_prog = None
        
        for si, sp in enumerate(progress.get("sections_progress", [])):
            if str(sp["section_id"]) == str(section_id):
                section_idx = si
                for ci, cp in enumerate(sp.get("chapters_progress", [])):
                    if str(cp["chapter_id"]) == str(chapter_id):
                        chapter_idx = ci
                        chapter_prog = cp
                        break
                break
        
        if not chapter_prog:
            return
        
        # Compter les quiz du chapitre
        total_quizzes = QuizModel.count_by_chapter(chapter_id)
        
        if total_quizzes == 0:
            chapter_prog["completion_percentage"] = 100
            chapter_prog["status"] = "completed"
        else:
            quizzes_progress = chapter_prog.get("quizzes_progress", [])
            passed_quizzes = len([q for q in quizzes_progress if q.get("status") == "passed"])
            
            # Calculer le pourcentage
            chapter_prog["completion_percentage"] = round((passed_quizzes / total_quizzes) * 100, 2)
            
            # Calculer le score moyen
            scores = [q.get("best_score", 0) for q in quizzes_progress if q.get("best_score", 0) > 0]
            chapter_prog["avg_score"] = round(sum(scores) / len(scores), 2) if scores else 0
            
            # Mettre à jour le statut
            if passed_quizzes == 0:
                chapter_prog["status"] = "not_started" if len(quizzes_progress) == 0 else "in_progress"
            elif passed_quizzes == total_quizzes:
                chapter_prog["status"] = "completed"
            else:
                chapter_prog["status"] = "in_progress"
        
        # Sauvegarder
        update_path = f"sections_progress.{section_idx}.chapters_progress.{chapter_idx}"
        UserProgressModel.get_collection().update_one(
            {
                "user_id": ObjectId(user_id),
                "church_id": ObjectId(church_id)
            },
            {
                "$set": {
                    update_path: chapter_prog,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Recalculer la progression de la section
        UserProgressModel.recalculate_section_progress(user_id, church_id, section_id)
    
    @staticmethod
    def recalculate_section_progress(user_id, church_id, section_id):
        """
        Recalcule la progression d'une section.
        """
        progress = UserProgressModel.get_or_create_progress(user_id, church_id)
        
        # Trouver la section
        section_idx = None
        section_prog = None
        
        for si, sp in enumerate(progress.get("sections_progress", [])):
            if str(sp["section_id"]) == str(section_id):
                section_idx = si
                section_prog = sp
                break
        
        if not section_prog:
            return
        
        chapters_progress = section_prog.get("chapters_progress", [])
        
        if not chapters_progress:
            section_prog["completion_percentage"] = 0
            section_prog["status"] = "not_started"
        else:
            # Calculer le pourcentage moyen
            total_percentage = sum(cp.get("completion_percentage", 0) for cp in chapters_progress)
            section_prog["completion_percentage"] = round(total_percentage / len(chapters_progress), 2)
            
            # Mettre à jour le statut
            completed_chapters = len([cp for cp in chapters_progress if cp.get("status") == "completed"])
            
            if completed_chapters == 0:
                in_progress = any(cp.get("status") == "in_progress" for cp in chapters_progress)
                section_prog["status"] = "in_progress" if in_progress else "not_started"
            elif completed_chapters == len(chapters_progress):
                section_prog["status"] = "completed"
                if not section_prog.get("completed_at"):
                    section_prog["completed_at"] = datetime.utcnow()
            else:
                section_prog["status"] = "in_progress"
                if not section_prog.get("started_at"):
                    section_prog["started_at"] = datetime.utcnow()
        
        # Sauvegarder
        update_path = f"sections_progress.{section_idx}"
        UserProgressModel.get_collection().update_one(
            {
                "user_id": ObjectId(user_id),
                "church_id": ObjectId(church_id)
            },
            {
                "$set": {
                    update_path: section_prog,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Recalculer les stats globales
        UserProgressModel.recalculate_overall_stats(user_id, church_id)
    
    @staticmethod
    def check_auto_unlock(user_id, church_id, section_id, completed_chapter_id):
        """
        Vérifie et débloque automatiquement le chapitre suivant si les conditions sont remplies.
        """
        from models.chapter_model import ChapterModel
        
        # Récupérer le chapitre complété
        completed_chapter = ChapterModel.get_chapter_by_id(completed_chapter_id)
        if not completed_chapter:
            return
        
        # Trouver le chapitre suivant
        next_chapter = ChapterModel.get_next_chapter(section_id, completed_chapter["order"])
        if not next_chapter:
            return  # Pas de chapitre suivant
        
        # Récupérer la progression
        progress = UserProgressModel.get_or_create_progress(user_id, church_id)
        
        # Trouver la progression du chapitre complété
        section_idx = None
        chapter_prog = None
        
        for si, sp in enumerate(progress.get("sections_progress", [])):
            if str(sp["section_id"]) == str(section_id):
                section_idx = si
                for cp in sp.get("chapters_progress", []):
                    if str(cp["chapter_id"]) == str(completed_chapter_id):
                        chapter_prog = cp
                        break
                break
        
        if not chapter_prog:
            return
        
        # Vérifier les conditions de déblocage
        unlock_requirements = next_chapter.get("unlock_requirements", {})
        min_score = unlock_requirements.get("min_score", 70)
        completion_required = unlock_requirements.get("completion_required", True)
        
        can_unlock = False
        
        if completion_required:
            # Le chapitre doit être complété
            if chapter_prog.get("status") == "completed" and chapter_prog.get("avg_score", 0) >= min_score:
                can_unlock = True
        else:
            # Juste besoin du score minimum
            if chapter_prog.get("avg_score", 0) >= min_score:
                can_unlock = True
        
        if can_unlock:
            UserProgressModel.unlock_chapter(user_id, church_id, section_id, str(next_chapter["_id"]), "auto")
    
    @staticmethod
    def unlock_chapter(user_id, church_id, section_id, chapter_id, unlocked_by="auto"):
        """
        Débloque un chapitre.
        """
        progress = UserProgressModel.get_or_create_progress(user_id, church_id)
        
        # Trouver le chapitre
        section_idx = None
        chapter_idx = None
        
        for si, sp in enumerate(progress.get("sections_progress", [])):
            if str(sp["section_id"]) == str(section_id):
                section_idx = si
                for ci, cp in enumerate(sp.get("chapters_progress", [])):
                    if str(cp["chapter_id"]) == str(chapter_id):
                        chapter_idx = ci
                        break
                break
        
        if section_idx is None or chapter_idx is None:
            return False
        
        # Débloquer
        update_path_unlocked = f"sections_progress.{section_idx}.chapters_progress.{chapter_idx}.is_unlocked"
        update_path_unlocked_at = f"sections_progress.{section_idx}.chapters_progress.{chapter_idx}.unlocked_at"
        update_path_unlocked_by = f"sections_progress.{section_idx}.chapters_progress.{chapter_idx}.unlocked_by"
        
        UserProgressModel.get_collection().update_one(
            {
                "user_id": ObjectId(user_id),
                "church_id": ObjectId(church_id)
            },
            {
                "$set": {
                    update_path_unlocked: True,
                    update_path_unlocked_at: datetime.utcnow(),
                    update_path_unlocked_by: unlocked_by,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return True
    
    @staticmethod
    def recalculate_overall_stats(user_id, church_id):
        """
        Recalcule les statistiques globales de l'utilisateur.
        """
        from models.quiz_attempt_model import QuizAttemptModel
        
        # Récupérer toutes les tentatives complétées
        attempts = list(QuizAttemptModel.get_collection().find({
            "user_id": ObjectId(user_id),
            "church_id": ObjectId(church_id),
            "status": "completed"
        }))
        
        total_quiz_completed = len(attempts)
        total_quiz_passed = len([a for a in attempts if a.get("passed")])
        avg_score = sum(a.get("score", 0) for a in attempts) / total_quiz_completed if total_quiz_completed > 0 else 0
        total_time_spent = sum(a.get("time_spent_seconds", 0) for a in attempts)
        
        # Calculer les streaks
        current_streak, longest_streak = UserProgressModel.calculate_streaks(user_id, church_id)
        
        overall_stats = {
            "total_quiz_completed": total_quiz_completed,
            "total_quiz_passed": total_quiz_passed,
            "avg_score": round(avg_score, 2),
            "total_time_spent_seconds": total_time_spent,
            "current_streak_days": current_streak,
            "longest_streak_days": longest_streak
        }
        
        UserProgressModel.get_collection().update_one(
            {
                "user_id": ObjectId(user_id),
                "church_id": ObjectId(church_id)
            },
            {
                "$set": {
                    "overall_stats": overall_stats,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    @staticmethod
    def calculate_streaks(user_id, church_id):
        """
        Calcule les streaks (séries de jours consécutifs) d'activité.
        """
        from models.quiz_attempt_model import QuizAttemptModel
        
        # Récupérer toutes les tentatives triées par date
        attempts = list(QuizAttemptModel.get_collection().find({
            "user_id": ObjectId(user_id),
            "church_id": ObjectId(church_id),
            "status": "completed"
        }).sort("submitted_at", 1))
        
        if not attempts:
            return 0, 0
        
        # Extraire les dates uniques
        dates = []
        for attempt in attempts:
            if attempt.get("submitted_at"):
                date = attempt["submitted_at"].date()
                if not dates or date != dates[-1]:
                    dates.append(date)
        
        if not dates:
            return 0, 0
        
        # Calculer le streak actuel
        current_streak = 0
        today = datetime.utcnow().date()
        
        # Vérifier si l'utilisateur a une activité aujourd'hui ou hier
        if dates[-1] == today or dates[-1] == today - timedelta(days=1):
            current_streak = 1
            for i in range(len(dates) - 2, -1, -1):
                expected_date = dates[i + 1] - timedelta(days=1)
                if dates[i] == expected_date:
                    current_streak += 1
                else:
                    break
        
        # Calculer le plus long streak
        longest_streak = 1
        temp_streak = 1
        
        for i in range(1, len(dates)):
            if dates[i] == dates[i - 1] + timedelta(days=1):
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1
        
        return current_streak, longest_streak