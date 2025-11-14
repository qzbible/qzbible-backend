# services/quiz_service.py

from bson import ObjectId
from models.quiz_attempt_model import QuizAttemptModel
from models.quiz_model import QuizModel
from models.chapter_model import ChapterModel
from models.user_model import UserModel

def create_quiz_service(data):
    """
    Crée un nouveau quiz.
    """
    # Vérifier que le chapitre existe
    chapter = ChapterModel.get_chapter_by_id(data["chapter_id"])
    if not chapter:
        return {"message": "Chapitre non trouvé"}, 404
    
    # Calculer l'ordre automatiquement si non fourni
    if not data.get("order"):
        data["order"] = QuizModel.get_next_order(data["chapter_id"])
    
    result = QuizModel.create_quiz(data)
    
    # Mettre à jour les stats du chapitre/section si nécessaire
    # TODO: Implémenter la mise à jour des stats
    
    return result, 201


def get_all_quizzes_service(chapter_id):
    """
    Récupère tous les quiz d'un chapitre.
    """
    if isinstance(chapter_id, dict) and "$oid" in chapter_id:
        chapter_id = chapter_id["$oid"]
    
    quizzes = QuizModel.get_all_quizzes_by_chapter(chapter_id)
    
    for quiz in quizzes:
        quiz["_id"] = str(quiz["_id"])
        quiz["chapter_id"] = str(quiz["chapter_id"])
        quiz["church_id"] = str(quiz["church_id"])
        
        if quiz.get("created_by"):
            quiz["created_by"] = str(quiz["created_by"])
        if quiz.get("source_quiz_id"):
            quiz["source_quiz_id"] = str(quiz["source_quiz_id"])
        
        # Convertir les ObjectId des questions et options
        for question in quiz.get("questions", []):
            question["_id"] = str(question["_id"])
            if "options" in question:
                for option in question["options"]:
                    option["_id"] = str(option["_id"])
    
    return quizzes



def get_quiz_by_id_service(quiz_id, include_answers=False):
    """
    Récupère un quiz par son ID.
    Si include_answers=False, masque les réponses correctes (pour les apprenants).
    """
    quiz = QuizModel.get_quiz_by_id(quiz_id)
    
    if not quiz:
        return None
    
    # Si on ne doit pas inclure les réponses (mode apprenant)
    if not include_answers:
        for question in quiz.get("questions", []):
            # Masquer les bonnes réponses pour QCM
            if "options" in question:
                for option in question["options"]:
                    option.pop("is_correct", None)
                    option.pop("points", None)
            
            # Masquer les réponses pour fill_blank et free_text
            question.pop("correct_answers", None)
            question.pop("free_text_answers", None)
            question.pop("explanation", None)
    
    return quiz


def update_quiz_service(quiz_id, data):
    """
    Met à jour un quiz.
    """
    return QuizModel.update_quiz(quiz_id, data)


def delete_quiz_service(quiz_id):
    """
    Supprime un quiz.
    """
    # Vérifier s'il y a des tentatives associées
    attempts_count = QuizModel.count_attempts_by_quiz(quiz_id)
    if attempts_count > 0:
        return {
            "message": f"Impossible de supprimer ce quiz. Il a {attempts_count} tentative(s) enregistrée(s).",
            "attempts_count": attempts_count
        }, 400
    
    result = QuizModel.delete_quiz(quiz_id)
    return result, 200


def get_quiz_stats_service(quiz_id):
    """
    Récupère les statistiques d'un quiz.
    """
    from models.quiz_attempt_model import QuizAttemptModel
    
    quiz = QuizModel.get_quiz_by_id(quiz_id)
    if not quiz:
        return {"message": "Quiz non trouvé"}, 404
    
    # Compter les tentatives
    total_attempts = QuizAttemptModel.get_collection().count_documents({
        "quiz_id": ObjectId(quiz_id)
    })
    
    # Compter les tentatives réussies
    passed_attempts = QuizAttemptModel.get_collection().count_documents({
        "quiz_id": ObjectId(quiz_id),
        "passed": True
    })
    
    # Calculer le score moyen
    attempts = list(QuizAttemptModel.get_collection().find({
        "quiz_id": ObjectId(quiz_id),
        "status": "completed"
    }))
    
    avg_score = 0
    if attempts:
        avg_score = sum(a.get("score", 0) for a in attempts) / len(attempts)
    
    # Calculer le temps moyen
    avg_time = 0
    if attempts:
        avg_time = sum(a.get("time_spent_seconds", 0) for a in attempts) / len(attempts)
    
    return {
        "quiz_id": quiz_id,
        "title": quiz["title"],
        "total_questions": len(quiz.get("questions", [])),
        "total_points": QuizModel.calculate_total_points(quiz_id),
        "total_attempts": total_attempts,
        "passed_attempts": passed_attempts,
        "pass_rate": (passed_attempts / total_attempts * 100) if total_attempts > 0 else 0,
        "avg_score": round(avg_score, 2),
        "avg_time_minutes": round(avg_time / 60, 2)
    }, 200


def clone_quiz_service(quiz_id, new_chapter_id, new_church_id, cloned_by):
    """
    Clone un quiz vers un nouveau chapitre.
    """
    original_quiz = QuizModel.get_quiz_by_id(quiz_id)
    
    if not original_quiz:
        return {"message": "Quiz non trouvé"}, 404
    
    # Créer le nouveau quiz
    cloned_data = {
        "chapter_id": new_chapter_id,
        "church_id": new_church_id,
        "title": original_quiz["title"],
        "description": original_quiz.get("description", ""),
        "order": QuizModel.get_next_order(new_chapter_id),
        "settings": original_quiz.get("settings", {}),
        "questions": original_quiz.get("questions", []),
        "is_public": False,
        "source_quiz_id": quiz_id,
        "created_by": cloned_by
    }
    
    # Retirer les _id existants pour en générer de nouveaux
    for question in cloned_data["questions"]:
        question.pop("_id", None)
        if "options" in question:
            for option in question["options"]:
                option.pop("_id", None)
    
    result = QuizModel.create_quiz(cloned_data)
    
    return {
        "message": "Quiz cloné avec succès",
        "quiz_id": result["quiz_id"]
    }, 201


def get_quizzes_with_last_attempt(chapter_id, user_id):
    """
    Récupère tous les quiz d'un chapitre avec la dernière tentative de l'utilisateur.
    Pour chaque quiz, retourne :
    - Les informations du quiz
    - Le score obtenu par l'utilisateur
    - Toutes les questions avec les réponses de l'utilisateur
    
    :param chapter_id: str ou ObjectId du chapitre
    :param user_id: str ou ObjectId de l'utilisateur
    :return: liste de dict contenant quiz, score et questions avec réponses
    """
   
    
    # 1. Récupérer tous les quiz du chapitre
    quizzes = QuizModel.get_all_quizzes_by_chapter(chapter_id)
    
    result = []
    
    for quiz in quizzes:
        quiz_id = str(quiz["_id"])
        
        # 2. Récupérer la dernière tentative pour ce quiz
        last_attempt = QuizAttemptModel.get_last_attempt(user_id, quiz_id)
        
        # 3. Préparer les données du quiz
        quiz_data = {
            "_id": quiz_id,
            "title": quiz.get("title"),
            "description": quiz.get("description"),
            "order": quiz.get("order"),
            "settings": quiz.get("settings", {})
        }
        
        # 4. Préparer les données de la tentative
        attempt_data = None
        questions_with_answers = []
        
        if last_attempt:
            # Créer un map des réponses par question_id
            answers_map = {}
            for answer in last_attempt.get("answers", []):
                question_id = str(answer["question_id"])
                answers_map[question_id] = answer
            
            # 5. Enrichir chaque question avec la réponse de l'utilisateur
            for question in quiz.get("questions", []):
                question_id = str(question.get("_id", ""))
                user_answer = answers_map.get(question_id)
                
                # Structure de base
                enriched_question = {
                    "question_id": question_id,
                    "order": question.get("order"),
                    "type": question.get("type"),
                    "question_text": question.get("question_text"),
                    "points_possible": question.get("points", 0),
                    "explanation": question.get("explanation"),
                    "media": question.get("media")
                }
                
                # Ajouter les options pour MCQ et True/False
                if question.get("type") in ["mcq_single", "mcq_multiple", "true_false"]:
                    options = []
                    selected_option_ids = []
                    
                    if user_answer:
                        selected_option_ids = [
                            str(opt_id) for opt_id in user_answer.get("selected_options", [])
                        ]
                    
                    for option in question.get("options", []):
                        option_id = str(option.get("_id", ""))
                        options.append({
                            "option_id": option_id,
                            "text": option.get("text"),
                            "is_correct": option.get("is_correct", False),
                            "is_selected": option_id in selected_option_ids,
                            "points": option.get("points", 0)
                        })
                    
                    enriched_question["options"] = options
                
                # Ajouter fill_blank_text pour fill_blank
                if question.get("type") == "fill_blank":
                    enriched_question["fill_blank_text"] = question.get("fill_blank_text")
                    enriched_question["correct_answers"] = question.get("correct_answers", [])
                    enriched_question["case_sensitive"] = question.get("case_sensitive", False)
                
                # Ajouter expected_answers pour free_text
                if question.get("type") == "free_text":
                    enriched_question["expected_answers"] = question.get("free_text_answers", [])
                    enriched_question["case_sensitive"] = question.get("case_sensitive", False)
                
                # Ajouter la réponse de l'utilisateur
                if user_answer:
                    enriched_question["user_answer"] = {
                        "selected_options": user_answer.get("selected_options", []),
                        "text_answer": user_answer.get("text_answer"),
                        "fill_blank_answers": user_answer.get("fill_blank_answers", [])
                    }
                    enriched_question["is_correct"] = user_answer.get("is_correct", False)
                    enriched_question["points_earned"] = user_answer.get("points_earned", 0)
                else:
                    enriched_question["user_answer"] = {
                        "selected_options": [],
                        "text_answer": None,
                        "fill_blank_answers": []
                    }
                    enriched_question["is_correct"] = False
                    enriched_question["points_earned"] = 0
                
                questions_with_answers.append(enriched_question)
            
            # 6. Données de la tentative
            attempt_data = {
                "attempt_id": str(last_attempt["_id"]),
                "attempt_number": last_attempt.get("attempt_number", 1),
                "status": last_attempt.get("status"),
                "score": round(last_attempt.get("score", 0), 2),
                "max_score": last_attempt.get("max_score", 100),
                "pass_score": last_attempt.get("pass_score", 70),
                "passed": last_attempt.get("passed", False),
                "time_spent_seconds": last_attempt.get("time_spent_seconds", 0),
                "started_at": last_attempt.get("started_at"),
                "submitted_at": last_attempt.get("submitted_at"),
                "created_at": last_attempt.get("created_at")
            }
        
        # 7. Ajouter au résultat
        result.append({
            "quiz": quiz_data,
            "last_attempt": attempt_data,
            "questions": questions_with_answers,
            "has_attempt": last_attempt is not None
        })
    
    return result
