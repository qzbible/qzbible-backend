# services/quiz_attempt_service.py

from bson import ObjectId
from datetime import datetime
from models.chapter_model import ChapterModel
from models.quiz_attempt_model import QuizAttemptModel
from models.quiz_model import QuizModel
from models.user_model import UserModel
from services.user_progress_service import update_user_progress_after_quiz

def start_quiz_attempt_service(quiz_id, user_id, church_id):
    """
    Démarre une nouvelle tentative de quiz.

    1. L'utilisateur (identifié par le JWT) veut passer un quiz
    2. Le système vérifie :
    ✅ Le quiz existe
    ✅ L'utilisateur a accès au chapitre contenant ce quiz
    ✅ L'utilisateur n'a pas dépassé le nombre max de tentatives
    ✅ Aucune tentative n'est déjà en cours pour ce quiz
    3. SI tout est OK :
    → Création d'une tentative (status: "in_progress")
    → Retour du quiz SANS les réponses correctes
    → Démarrage du timer (si limite de temps configurée)
    4. L'utilisateur peut maintenant répondre aux questions
    """
    # Récupérer le quiz
    quiz = QuizModel.get_quiz_by_id(quiz_id)
    if not quiz:
        return {"message": "Quiz non trouvé"}, 404
    
    # Vérifier le nombre de tentatives si limité
    max_attempts = quiz.get("settings", {}).get("max_attempts", 0)
    if max_attempts > 0:
        attempt_count = QuizAttemptModel.count_user_attempts(user_id, quiz_id)
        if attempt_count >= max_attempts:
            print(f"[WARN] Utilisateur {user_id} a atteint le nombre maximum de tentatives pour le quiz {quiz_id}")
            # return {
            #     "message": f"Nombre maximum de tentatives atteint ({max_attempts})",
            #     "attempts_used": attempt_count
            # }, 403 
            
    
    # Calculer le numéro de tentative
    attempt_number = QuizAttemptModel.count_user_attempts(user_id, quiz_id) + 1
    
    # Calculer le score maximum
    max_score = QuizModel.calculate_total_points(quiz_id)
    pass_score = quiz.get("settings", {}).get("pass_score", 70)
    
    # Créer la tentative
    data = {
        "quiz_id": quiz_id,
        "user_id": user_id,
        "church_id": church_id,
        "attempt_number": attempt_number,
        "max_score": max_score,
        "pass_score": pass_score
    }
    
    result = QuizAttemptModel.create_attempt(data)
    
    # Retourner aussi les infos du quiz (sans les réponses)
    quiz_info = QuizModel.get_quiz_by_id(quiz_id, include_answers=False)
    result["quiz"] = quiz_info
    
    return result, 201

# services/quiz_attempt_service.py

def submit_quiz_attempt_service(attempt_id, answers, user_id):
    """
    Soumet une tentative de quiz et calcule le score.
    Si la tentative a déjà été soumise, remplace les réponses et recalcule le score.
    Gère tous les types de questions : mcq_single, mcq_multiple, true_false, fill_blank, free_text
    """
    
    
    # 1. Récupérer la tentative
    attempt = QuizAttemptModel.get_attempt_by_id(attempt_id)
    
    if not attempt:
        return {"message": "Tentative non trouvée"}, 404
    
    # 2. Vérifier que la tentative appartient à l'utilisateur
    if str(attempt["user_id"]) != str(user_id):
        return {"message": "Accès non autorisé à cette tentative"}, 403
    
    # 3. 🎯 Vérifier si la tentative a déjà été soumise
    was_already_submitted = attempt.get("status") == "completed"
    
    if was_already_submitted:
        print(f"[INFO] Tentative {attempt_id} déjà soumise - Remplacement des réponses")
    
    # 4. Récupérer le quiz complet
    quiz = QuizModel.get_quiz_by_id(str(attempt["quiz_id"]))
    
    if not quiz:
        return {"message": "Quiz non trouvé"}, 404
    
    # 5. Vérifier le nombre maximum de tentatives
    max_attempts = quiz.get("settings", {}).get("max_attempts", 0)
    
    if max_attempts > 0 and was_already_submitted:
        # Compter le nombre de tentatives déjà effectuées
        attempt_number = attempt.get("attempt_number", 1)
        
        if attempt_number >= max_attempts:
            return {
                "message": f"Nombre maximum de tentatives atteint ({max_attempts})",
                "max_attempts": max_attempts,
                "current_attempt": attempt_number
            }, 400
    
    # 6. Créer un map des questions par ID
    questions_map = {}
    for question in quiz.get("questions", []):
        question_id = str(question.get("_id", ""))
        questions_map[question_id] = question
    
    # 7. Évaluer chaque réponse
    evaluated_answers = []
    total_points_earned = 0
    total_points_possible = 0
    
    for answer in answers:
        question_id = str(answer.get("question_id"))
        question = questions_map.get(question_id)
        
        if not question:
            continue
        
        question_type = answer.get("question_type") or question.get("type")
        points_possible = question.get("points", 0)
        total_points_possible += points_possible
        
        # Évaluer selon le type de question
        if question_type == "mcq_single":
            result = evaluate_mcq_single(answer, question)
        elif question_type == "mcq_multiple":
            result = evaluate_mcq_multiple(answer, question)
        elif question_type == "true_false":
            result = evaluate_true_false(answer, question)
        elif question_type == "fill_blank":
            result = evaluate_fill_blank(answer, question)
        elif question_type == "free_text":
            result = evaluate_free_text(answer, question)
        else:
            result = {
                "is_correct": False,
                "points_earned": 0
            }
        
        total_points_earned += result["points_earned"]
        
        # Construire la réponse évaluée
        evaluated_answer = {
            "question_id": question_id,
            "question_type": question_type,
            "selected_options": answer.get("selected_options", []),
            "fill_blank_answers": answer.get("fill_blank_answers", []),
            "text_answer": answer.get("free_text_answer"),
            "is_correct": result["is_correct"],
            "points_earned": result["points_earned"],
            "points_possible": points_possible,
            "time_spent_seconds": answer.get("time_spent_seconds", 0)
        }
        
        evaluated_answers.append(evaluated_answer)
    
    # 8. Calculer le score en pourcentage
    if total_points_possible > 0:
        score_percentage = (total_points_earned / total_points_possible) * 100
    else:
        score_percentage = 0
    
    pass_score = quiz.get("settings", {}).get("pass_score", 70)
    passed = score_percentage >= pass_score
    
    # 9. Calculer le temps total passé
    total_time_spent = sum(a.get("time_spent_seconds", 0) for a in answers)
    
    # 10. 🎯 Mettre à jour la tentative dans la base de données
    submitted_at = datetime.utcnow()
    
    update_data = {
        "status": "completed",
        "submitted_at": submitted_at,
        "answers": evaluated_answers,
        "score": round(score_percentage, 2),
        "max_score": 100,
        "pass_score": pass_score,
        "passed": passed,
        "time_spent_seconds": total_time_spent,
        "updated_at": submitted_at
    }
    
    # 🎯 Si c'était déjà soumis, incrémenter le numéro de tentative
    if was_already_submitted:
        current_attempt_number = attempt.get("attempt_number", 1)
        update_data["attempt_number"] = current_attempt_number + 1
    
    QuizAttemptModel.update_attempt(attempt_id, update_data)
    
    # 11. 🎯 Mettre à jour la progression de l'utilisateur
    # Toujours mettre à jour, même si c'est une re-soumission
    from services.user_progress_service import update_user_progress_after_quiz
    
    chapter = ChapterModel.get_chapter_by_id(str(quiz["chapter_id"]))
    if chapter:
        update_user_progress_after_quiz(
            user_id=user_id,
            quiz_id=str(quiz["_id"]),
            chapter_id=str(quiz["chapter_id"]),
            church_id=str(attempt["church_id"]),
            score_percentage=score_percentage,
            passed=passed
        )
    
    # 12. Construire la réponse
    result = {
        "message": "Tentative soumise avec succès" if not was_already_submitted else "Tentative mise à jour avec succès",
        "data": {
            "_id": str(attempt["_id"]),
            "quiz_id": str(quiz["_id"]),
            "status": "completed",
            "score": round(score_percentage, 2),
            "passed": passed,
            "time_spent_seconds": total_time_spent,
            "submitted_at": submitted_at,
            "attempt_number": update_data.get("attempt_number", attempt.get("attempt_number", 1)),
            "answers": evaluated_answers,
            "is_resubmission": was_already_submitted
        },
        "result": {
            "score": round(score_percentage, 2),
            "max_score": 100,
            "points_earned": total_points_earned,
            "points_possible": total_points_possible,
            "passed": passed,
            "pass_score": pass_score
        }
    }
    
    return result, 200


# Les fonctions d'évaluation restent les mêmes
def evaluate_mcq_single(answer, question):
    """
    Évalue une question à choix unique (MCQ Single).
    """
    selected_options = answer.get("selected_options", [])
    
    if not selected_options:
        return {"is_correct": False, "points_earned": 0}
    
    selected_option_id = str(selected_options[0])
    
    for option in question.get("options", []):
        if str(option.get("_id", "")) == selected_option_id:
            if option.get("is_correct", False):
                return {
                    "is_correct": True,
                    "points_earned": question.get("points", 0)
                }
            else:
                return {"is_correct": False, "points_earned": 0}
    
    return {"is_correct": False, "points_earned": 0}


def evaluate_mcq_multiple(answer, question):
    """
    Évalue une question à choix multiples (MCQ Multiple).
    """
    selected_options = [str(opt) for opt in answer.get("selected_options", [])]
    
    if not selected_options:
        return {"is_correct": False, "points_earned": 0}
    
    points_earned = 0
    total_correct_options = 0
    correct_selections = 0
    incorrect_selections = 0
    
    for option in question.get("options", []):
        option_id = str(option.get("_id", ""))
        is_correct = option.get("is_correct", False)
        is_selected = option_id in selected_options
        
        if is_correct:
            total_correct_options += 1
            if is_selected:
                correct_selections += 1
                points_earned += option.get("points", 0)
        else:
            if is_selected:
                incorrect_selections += 1
    
    if incorrect_selections > 0:
        points_earned = max(0, points_earned - incorrect_selections)
    
    is_correct = (correct_selections == total_correct_options and incorrect_selections == 0)
    
    return {
        "is_correct": is_correct,
        "points_earned": points_earned
    }


def evaluate_true_false(answer, question):
    """
    Évalue une question Vrai/Faux (True/False).
    """
    selected_options = answer.get("selected_options", [])
    
    if not selected_options:
        return {"is_correct": False, "points_earned": 0}
    
    selected_option_id = str(selected_options[0])
    
    for option in question.get("options", []):
        if str(option.get("_id", "")) == selected_option_id:
            if option.get("is_correct", False):
                return {
                    "is_correct": True,
                    "points_earned": question.get("points", 0)
                }
            else:
                return {"is_correct": False, "points_earned": 0}
    
    return {"is_correct": False, "points_earned": 0}


def evaluate_fill_blank(answer, question):
    """
    Évalue une question à trous (Fill in the Blank).
    """
    user_answers = answer.get("fill_blank_answers", [])
    correct_answers = question.get("correct_answers", [])
    case_sensitive = question.get("case_sensitive", False)
    
    if len(user_answers) != len(correct_answers):
        return {"is_correct": False, "points_earned": 0}
    
    all_correct = True
    
    for user_ans, correct_ans in zip(user_answers, correct_answers):
        if case_sensitive:
            if user_ans != correct_ans:
                all_correct = False
                break
        else:
            if user_ans.lower().strip() != correct_ans.lower().strip():
                all_correct = False
                break
    
    if all_correct:
        return {
            "is_correct": True,
            "points_earned": question.get("points", 0)
        }
    else:
        return {"is_correct": False, "points_earned": 0}


def evaluate_free_text(answer, question):
    """
    Évalue une question à réponse libre (Free Text).
    """
    user_answer = answer.get("free_text_answer", "")
    expected_answers = question.get("free_text_answers", [])
    case_sensitive = question.get("case_sensitive", False)
    
    if not user_answer:
        return {"is_correct": False, "points_earned": 0}
    
    if not case_sensitive:
        user_answer = user_answer.lower()
        expected_answers = [ans.lower() for ans in expected_answers]
    
    for expected in expected_answers:
        if expected in user_answer:
            return {
                "is_correct": True,
                "points_earned": question.get("points", 0)
            }
    
    keywords_found = sum(1 for exp in expected_answers if exp in user_answer)
    
    if keywords_found > 0:
        partial_points = (keywords_found / len(expected_answers)) * question.get("points", 0)
        return {
            "is_correct": False,
            "points_earned": int(partial_points)
        }
    
    return {"is_correct": False, "points_earned": 0}



def evaluate_mcq_answer(question, selected_options):
    """
    Évalue une réponse QCM.
    """
    question_type = question.get("type")
    options = question.get("options", [])
    
    # Créer des sets pour comparaison
    selected_set = set(str(opt_id) for opt_id in selected_options)
    correct_set = set(str(opt["_id"]) for opt in options if opt.get("is_correct"))
    
    if question_type == "mcq_single" or question_type == "true_false":
        # Une seule bonne réponse
        is_correct = selected_set == correct_set
        points = question.get("points", 0) if is_correct else 0
        
    elif question_type == "mcq_multiple":
        # Plusieurs bonnes réponses - scoring partiel
        correct_selected = selected_set & correct_set
        incorrect_selected = selected_set - correct_set
        
        # Points par bonne réponse
        points_per_correct = question.get("points", 0) / len(correct_set) if correct_set else 0
        
        # Calculer les points
        points = len(correct_selected) * points_per_correct
        
        # Pénalité pour les mauvaises réponses (optionnel)
        # points -= len(incorrect_selected) * (points_per_correct / 2)
        # points = max(0, points)
        
        is_correct = selected_set == correct_set
    
    return is_correct, round(points, 2)


def evaluate_fill_blank_answer(question, user_answers):
    """
    Évalue une réponse fill_blank.
    """
    correct_answers = question.get("correct_answers", [])
    
    if len(user_answers) != len(correct_answers):
        return False, 0
    
    # Comparer chaque réponse (insensible à la casse par défaut)
    all_correct = True
    for user_ans, correct_ans in zip(user_answers, correct_answers):
        if user_ans.strip().lower() != correct_ans.strip().lower():
            all_correct = False
            break
    
    points = question.get("points", 0) if all_correct else 0
    return all_correct, points


def evaluate_free_text_answer(question, user_answer):
    """
    Évalue une réponse free_text.
    """
    accepted_answers = question.get("free_text_answers", [])
    case_sensitive = question.get("case_sensitive", False)
    
    user_answer_normalized = user_answer.strip()
    if not case_sensitive:
        user_answer_normalized = user_answer_normalized.lower()
    
    is_correct = False
    for accepted in accepted_answers:
        accepted_normalized = accepted.strip()
        if not case_sensitive:
            accepted_normalized = accepted_normalized.lower()
        
        if user_answer_normalized == accepted_normalized:
            is_correct = True
            break
    
    points = question.get("points", 0) if is_correct else 0
    return is_correct, points


def get_user_attempts_service(user_id, quiz_id=None):
    """
    Récupère toutes les tentatives d'un utilisateur.
    """
    attempts = QuizAttemptModel.get_attempts_by_user(user_id, quiz_id)
    
    for attempt in attempts:
        attempt["_id"] = str(attempt["_id"])
        attempt["quiz_id"] = str(attempt["quiz_id"])
        attempt["user_id"] = str(attempt["user_id"])
        attempt["church_id"] = str(attempt["church_id"])
        
        # Convertir les ObjectId dans les réponses
        for answer in attempt.get("answers", []):
            answer["question_id"] = str(answer["question_id"])
            if "selected_options" in answer:
                answer["selected_options"] = [str(opt_id) for opt_id in answer["selected_options"]]
    
    return attempts


def get_attempt_by_id_service(attempt_id, user_id):
    """
    Récupère une tentative par son ID. 
    """
    attempt = QuizAttemptModel.get_attempt_by_id(attempt_id)
    
    if not attempt:
        return {"message": "Tentative non trouvée"}, 404
    
    # Vérifier l'accès (l'utilisateur doit être le propriétaire ou admin)
    if attempt["user_id"] != str(user_id):
        # TODO: Vérifier si c'est un admin
        return {"message": "Accès non autorisé"}, 403
    
    return attempt, 200


def abandon_attempt_service(attempt_id, user_id):
    """
    Abandonne une tentative.
    """
    attempt = QuizAttemptModel.get_attempt_by_id(attempt_id)
    
    if not attempt:
        return {"message": "Tentative non trouvée"}, 404
    
    if attempt["user_id"] != str(user_id):
        return {"message": "Accès non autorisé"}, 403
    
    if attempt["status"] != "in_progress":
        return {"message": "Cette tentative ne peut pas être abandonnée"}, 400
    
    QuizAttemptModel.abandon_attempt(attempt_id)
    
    return {"message": "Tentative abandonnée"}, 200

# services/quiz_attempt_service.py

# def get_attempt_with_questions_service(attempt_id, user_id):
#     """
#     Récupère une tentative avec toutes les questions et réponses du quiz.
#     """
 
#     # 1. Récupérer la tentative
#     attempt = QuizAttemptModel.get_attempt_by_id(attempt_id)
    
#     if not attempt:
#         return {"message": "Tentative non trouvée"}, 404
    
#     # 2. Vérifier que la tentative appartient à l'utilisateur
#     if str(attempt["user_id"]) != str(user_id):
#         return {"message": "Accès non autorisé à cette tentative"}, 403
    
#     # 3. Récupérer le quiz complet
#     quiz = QuizModel.get_quiz_by_id(str(attempt["quiz_id"]))
    
#     if not quiz:
#         return {"message": "Quiz non trouvé"}, 404
    
#     # 4. Créer un map des réponses de l'utilisateur
#     user_answers_map = {}
#     for answer in attempt.get("answers", []):
#         question_id = str(answer["question_id"])
#         user_answers_map[question_id] = answer
    
#     # 5. Enrichir chaque question avec la réponse de l'utilisateur
#     enriched_questions = []
    
#     for question in quiz.get("questions", []):
#         question_id = str(question.get("_id", ""))
#         user_answer = user_answers_map.get(question_id)
        
#         # Structure de base de la question
#         enriched_question = {
#             "question_id": question_id,
#             "order": question.get("order"),
#             "type": question.get("type"),
#             "question_text": question.get("question_text"),
#             "points_possible": question.get("points", 0),
#             "explanation": question.get("explanation"),
#             "media": question.get("media")
#         }
        
#         # 🎯 Ajouter les options pour MCQ et True/False
#         if question.get("type") in ["mcq_single", "mcq_multiple", "true_false"]:
#             options = []
#             selected_option_ids = []
            
#             if user_answer:
#                 selected_option_ids = [
#                     str(opt_id) for opt_id in user_answer.get("selected_options", [])
#                 ]
            
#             for option in question.get("options", []):
#                 option_id = str(option.get("_id", ""))
#                 options.append({
#                     "option_id": option_id,
#                     "text": option.get("text"),
#                     "is_correct": option.get("is_correct", False),
#                     "is_selected": option_id in selected_option_ids,
#                     "points": option.get("points", 0)  # Pour mcq_multiple
#                 })
            
#             enriched_question["options"] = options
        
#         # 🎯 Ajouter fill_blank_text pour fill_blank
#         if question.get("type") == "fill_blank":
#             enriched_question["fill_blank_text"] = question.get("fill_blank_text")
#             enriched_question["correct_answers"] = question.get("correct_answers", [])
#             enriched_question["case_sensitive"] = question.get("case_sensitive", False)
        
#         # 🎯 Ajouter free_text_answers pour free_text
#         if question.get("type") == "free_text":
#             enriched_question["expected_answers"] = question.get("free_text_answers", [])
#             enriched_question["case_sensitive"] = question.get("case_sensitive", False)
        
#         # 🎯 Ajouter la réponse de l'utilisateur
#         if user_answer:
#             user_answer_data = {
#                 "selected_options": user_answer.get("selected_options", []),
#                 "text_answer": user_answer.get("text_answer"),
#                 "fill_blank_answers": user_answer.get("fill_blank_answers", [])
#             }
            
#             enriched_question["user_answer"] = user_answer_data
#             enriched_question["is_correct"] = user_answer.get("is_correct", False)
#             enriched_question["points_earned"] = user_answer.get("points_earned", 0)
#         else:
#             # Question non répondue
#             enriched_question["user_answer"] = None
#             enriched_question["is_correct"] = False
#             enriched_question["points_earned"] = 0
        
#         enriched_questions.append(enriched_question)
    
#     # 6. Construire la réponse finale
#     result = {
#         "_id": str(attempt["_id"]),
#         "quiz_id": str(attempt["quiz_id"]),
#         "quiz_title": quiz.get("title"),
#         "quiz_description": quiz.get("description"),
#         "user_id": str(attempt["user_id"]),
#         "church_id": str(attempt["church_id"]),
#         "attempt_number": attempt.get("attempt_number"),
#         "status": attempt.get("status"),
#         "started_at": attempt.get("started_at"),
#         "submitted_at": attempt.get("submitted_at"),
#         "time_spent_seconds": attempt.get("time_spent_seconds", 0),
#         "score": round(attempt.get("score", 0), 2),
#         "max_score": attempt.get("max_score", 0),
#         "pass_score": attempt.get("pass_score", 70),
#         "passed": attempt.get("passed", False),
#         "questions": enriched_questions,
#         "created_at": attempt.get("created_at")
#     }
    
#     return result, 200



def get_attempt_with_questions_service(attempt_id, user_id):
    """
    Récupère une tentative avec toutes les questions et réponses du quiz.
    
    IMPORTANT: Retourne TOUTES les questions du quiz, même celles non répondues,
    avec les réponses de l'utilisateur pour cet attempt_id spécifique.
    """
   
    
    # 1. Récupérer la tentative
    attempt = QuizAttemptModel.get_attempt_by_id(attempt_id)
    
    if not attempt:
        return {"message": "Tentative non trouvée"}, 404
    
    # 2. Vérifier que la tentative appartient à l'utilisateur
    if str(attempt["user_id"]) != str(user_id):
        return {"message": "Accès non autorisé à cette tentative"}, 403
    
    # 3. Récupérer le quiz complet
    quiz = QuizModel.get_quiz_by_id(str(attempt["quiz_id"]))
    
    if not quiz:
        return {"message": "Quiz non trouvé"}, 404
    
    # 4. Créer un map des réponses de l'utilisateur pour cette tentative
    user_answers_map = {}
    for answer in attempt.get("answers", []):
        question_id = str(answer["question_id"])
        user_answers_map[question_id] = answer
    
    # 5. 🎯 Enrichir TOUTES les questions avec les réponses de l'utilisateur
    enriched_questions = []
    
    for question in quiz.get("questions", []):
        question_id = str(question.get("_id", ""))
        user_answer = user_answers_map.get(question_id)
        
        # Structure de base de la question
        enriched_question = {
            "question_id": question_id,
            "order": question.get("order"),
            "type": question.get("type"),
            "question_text": question.get("question_text"),
            "points_possible": question.get("points", 0),
            "explanation": question.get("explanation"),
            "media": question.get("media")
        }
        
        # 🎯 Ajouter les options pour MCQ et True/False
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
                    "points": option.get("points", 0)  # Pour mcq_multiple
                })
            
            enriched_question["options"] = options
        
        # 🎯 Ajouter fill_blank_text pour fill_blank
        if question.get("type") == "fill_blank":
            enriched_question["fill_blank_text"] = question.get("fill_blank_text")
            enriched_question["correct_answers"] = question.get("correct_answers", [])
            enriched_question["case_sensitive"] = question.get("case_sensitive", False)
        
        # 🎯 Ajouter free_text_answers pour free_text
        if question.get("type") == "free_text":
            enriched_question["expected_answers"] = question.get("free_text_answers", [])
            enriched_question["case_sensitive"] = question.get("case_sensitive", False)
        
        # 🎯 Ajouter la réponse de l'utilisateur (même si None)
        if user_answer:
            # L'utilisateur a répondu à cette question
            user_answer_data = {
                "selected_options": user_answer.get("selected_options", []),
                "text_answer": user_answer.get("text_answer"),
                "fill_blank_answers": user_answer.get("fill_blank_answers", [])
            }
            
            enriched_question["user_answer"] = user_answer_data
            enriched_question["is_correct"] = user_answer.get("is_correct", False)
            enriched_question["points_earned"] = user_answer.get("points_earned", 0)
        else:
            # 🎯 L'utilisateur n'a PAS répondu à cette question
            enriched_question["user_answer"] = {
                "selected_options": [],
                "text_answer": None,
                "fill_blank_answers": []
            }
            enriched_question["is_correct"] = False
            enriched_question["points_earned"] = 0
        
        # 🎯 Toujours ajouter la question (répondue ou non)
        enriched_questions.append(enriched_question)
    
    # 6. Calculer les statistiques
    total_questions = len(enriched_questions)
    answered_questions = len([q for q in enriched_questions if q["user_answer"] and (
        q["user_answer"]["selected_options"] or 
        q["user_answer"]["text_answer"] or 
        q["user_answer"]["fill_blank_answers"]
    )])
    correct_answers = len([q for q in enriched_questions if q["is_correct"]])
    
    # 7. Construire la réponse finale
    result = {
        "_id": str(attempt["_id"]),
        "quiz_id": str(attempt["quiz_id"]),
        "quiz_title": quiz.get("title"),
        "quiz_description": quiz.get("description"),
        "user_id": str(attempt["user_id"]),
        "church_id": str(attempt["church_id"]),
        "attempt_number": attempt.get("attempt_number"),
        "status": attempt.get("status"),
        "started_at": attempt.get("started_at"),
        "submitted_at": attempt.get("submitted_at"),
        "time_spent_seconds": attempt.get("time_spent_seconds", 0),
        "score": round(attempt.get("score", 0), 2),
        "max_score": attempt.get("max_score", 100),
        "pass_score": attempt.get("pass_score", 70),
        "passed": attempt.get("passed", False),
        "statistics": {
            "total_questions": total_questions,
            "answered_questions": answered_questions,
            "unanswered_questions": total_questions - answered_questions,
            "correct_answers": correct_answers,
            "incorrect_answers": answered_questions - correct_answers,
            "accuracy": round((correct_answers / answered_questions * 100) if answered_questions > 0 else 0, 2)
        },
        "questions": enriched_questions,
        "created_at": attempt.get("created_at")
    }
    
    return result, 200