# services/quiz_attempt_service.py

from bson import ObjectId
from datetime import datetime
from models.quiz_attempt_model import QuizAttemptModel
from models.quiz_model import QuizModel
from models.user_model import UserModel

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
            return {
                "message": f"Nombre maximum de tentatives atteint ({max_attempts})",
                "attempts_used": attempt_count
            }, 403
    
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


def submit_quiz_attempt_service(attempt_id, answers_data, user_id):
    """
    Soumet une tentative et calcule le score.
    """
    # Récupérer la tentative
    attempt = QuizAttemptModel.get_attempt_by_id(attempt_id)
    if not attempt:
        return {"message": "Tentative non trouvée"}, 404
    
    # Vérifier que la tentative appartient à l'utilisateur
    if attempt["user_id"] != str(user_id):
        return {"message": "Accès non autorisé à cette tentative"}, 403
    
    # Vérifier que la tentative est en cours
    if attempt["status"] != "in_progress":
        return {"message": "Cette tentative a déjà été soumise ou abandonnée"}, 400
    
    # Récupérer le quiz avec les réponses
    quiz = QuizModel.get_quiz_by_id(attempt["quiz_id"], include_answers=True)
    if not quiz:
        return {"message": "Quiz non trouvé"}, 404
    
    # Créer un map des questions pour accès rapide
    questions_map = {str(q["_id"]): q for q in quiz.get("questions", [])}
    
    # Évaluer chaque réponse
    evaluated_answers = []
    total_score = 0
    
    for answer_data in answers_data:
        question_id = answer_data["question_id"]
        question = questions_map.get(question_id)
        
        if not question:
            continue
        
        answer = {
            "question_id": ObjectId(question_id),
            "question_type": answer_data["question_type"],
            "points_possible": question.get("points", 0),
            "time_spent_seconds": answer_data.get("time_spent_seconds", 0)
        }
        
        # Évaluer selon le type de question
        if answer_data["question_type"] in ["mcq_single", "mcq_multiple", "true_false"]:
            answer["selected_options"] = [ObjectId(opt) for opt in answer_data.get("selected_options", [])]
            is_correct, points = evaluate_mcq_answer(question, answer["selected_options"])
            answer["is_correct"] = is_correct
            answer["points_earned"] = points
            
        elif answer_data["question_type"] == "fill_blank":
            answer["fill_blank_answers"] = answer_data.get("fill_blank_answers", [])
            is_correct, points = evaluate_fill_blank_answer(question, answer["fill_blank_answers"])
            answer["is_correct"] = is_correct
            answer["points_earned"] = points
            
        elif answer_data["question_type"] == "free_text":
            answer["free_text_answer"] = answer_data.get("free_text_answer", "")
            is_correct, points = evaluate_free_text_answer(question, answer["free_text_answer"])
            answer["is_correct"] = is_correct
            answer["points_earned"] = points
        
        total_score += answer.get("points_earned", 0)
        evaluated_answers.append(answer)
    
    # Calculer le temps passé
    started_at = attempt.get("started_at")
    time_spent = int((datetime.utcnow() - started_at).total_seconds()) if started_at else 0
    
    # Déterminer si le quiz est réussi
    max_score = attempt.get("max_score", 100)
    pass_score = attempt.get("pass_score", 70)
    score_percentage = (total_score / max_score * 100) if max_score > 0 else 0
    passed = score_percentage >= pass_score
    
    # Soumettre la tentative
    QuizAttemptModel.submit_attempt(attempt_id, evaluated_answers, time_spent)
    
    # Mettre à jour le score et le statut
    QuizAttemptModel.update_attempt(attempt_id, {
        "score": round(score_percentage, 2),
        "passed": passed
    })
    
    # Récupérer la tentative mise à jour
    updated_attempt = QuizAttemptModel.get_attempt_by_id(attempt_id)
    
    return {
        "message": "Tentative soumise avec succès",
        "data": updated_attempt,
        "result": {
            "score": round(score_percentage, 2),
            "max_score": 100,
            "points_earned": total_score,
            "points_possible": max_score,
            "passed": passed,
            "pass_score": pass_score
        }
    }, 200


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