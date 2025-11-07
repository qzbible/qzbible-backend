# models/quiz_attempt_model.py

from bson import ObjectId
from datetime import datetime
from extensions import mongo
from models.quiz_model import QuizModel

class QuizAttemptModel:
    
    collection = mongo.db.quiz_attempts
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.quiz_attempts
    
    @staticmethod
    def create_attempt(data):
        """
        Crée une nouvelle tentative de quiz.
        
        :param data: dict contenant les informations de la tentative
        :return: dict contenant le message de succès et l'ID de la tentative
        """
        attempt = {
            "quiz_id": ObjectId(data["quiz_id"]),
            "user_id": ObjectId(data["user_id"]),
            "church_id": ObjectId(data["church_id"]),
            "attempt_number": data.get("attempt_number", 1),
            "status": "in_progress",
            "started_at": datetime.utcnow(),
            "submitted_at": None,
            "time_spent_seconds": 0,
            "score": 0,
            "max_score": data.get("max_score", 0),
            "pass_score": data.get("pass_score", 70),
            "passed": False,
            "answers": [],
            "created_at": datetime.utcnow()
        }
        
        result = QuizAttemptModel.get_collection().insert_one(attempt)
        
        return {
            "message": "Tentative démarrée avec succès",
            "attempt_id": str(result.inserted_id)
        }
    
    @staticmethod
    def get_attempt_by_id(attempt_id):
        """
        Récupère une tentative par son ID.
        """
        attempt = QuizAttemptModel.get_collection().find_one({"_id": ObjectId(attempt_id)})
        if attempt:
            attempt["_id"] = str(attempt["_id"])
            attempt["quiz_id"] = str(attempt["quiz_id"])
            attempt["user_id"] = str(attempt["user_id"])
            attempt["church_id"] = str(attempt["church_id"])
            
            # Convertir les ObjectId dans les réponses
            for answer in attempt.get("answers", []):
                answer["question"] = QuizModel.get_question_by_id(str(attempt["quiz_id"]), str(answer["question_id"]))
                if "selected_options" in answer:
                    answer["selected_options"] = [str(opt_id) for opt_id in answer["selected_options"]]
        
        return attempt
    
    @staticmethod
    def get_attempts_by_user(user_id, quiz_id=None):
        """
        Récupère toutes les tentatives d'un utilisateur.
        """
        query = {"user_id": ObjectId(user_id)}
        if quiz_id:
            query["quiz_id"] = ObjectId(quiz_id)
        
        attempts = QuizAttemptModel.get_collection().find(query).sort("created_at", -1)
        return list(attempts)
    
    @staticmethod
    def get_attempts_by_quiz(quiz_id):
        """
        Récupère toutes les tentatives d'un quiz.
        """
        attempts = QuizAttemptModel.get_collection().find({
            "quiz_id": ObjectId(quiz_id)
        }).sort("created_at", -1)
        return list(attempts)
    
    @staticmethod
    def count_user_attempts(user_id, quiz_id):
        """
        Compte le nombre de tentatives d'un utilisateur pour un quiz.
        """
        return QuizAttemptModel.get_collection().count_documents({
            "user_id": ObjectId(user_id),
            "quiz_id": ObjectId(quiz_id)
        })
    
    @staticmethod
    def update_attempt(attempt_id, data):
        """
        Met à jour une tentative.
        """
        update_data = {k: data[k] for k in data if k in [
            "status", "submitted_at", "time_spent_seconds", 
            "score", "passed", "answers"
        ]}
        
        # Convertir les ObjectId dans les réponses si nécessaire
        if "answers" in update_data:
            for answer in update_data["answers"]:
                if "question_id" in answer and isinstance(answer["question_id"], str):
                    answer["question_id"] = ObjectId(answer["question_id"])
                if "selected_options" in answer:
                    answer["selected_options"] = [
                        ObjectId(opt_id) if isinstance(opt_id, str) else opt_id 
                        for opt_id in answer["selected_options"]
                    ]
        
        result = QuizAttemptModel.get_collection().update_one(
            {"_id": ObjectId(attempt_id)},
            {"$set": update_data}
        )
        
        return {
            "message": "Tentative mise à jour avec succès",
            "modified_count": result.modified_count
        }
    
    @staticmethod
    def add_or_update_answer(attempt_id, answer):
        """
        Ajoute ou met à jour une réponse dans une tentative en cours.
        """
        # Convertir les IDs
        answer["question_id"] = ObjectId(answer["question_id"])
        if "selected_options" in answer:
            answer["selected_options"] = [
                ObjectId(opt_id) if isinstance(opt_id, str) else opt_id 
                for opt_id in answer["selected_options"]
            ]
        
        # Vérifier si la réponse existe déjà
        attempt = QuizAttemptModel.get_collection().find_one({"_id": ObjectId(attempt_id)})
        
        existing_answer_index = None
        for i, ans in enumerate(attempt.get("answers", [])):
            if ans["question_id"] == answer["question_id"]:
                existing_answer_index = i
                break
        
        if existing_answer_index is not None:
            # Mettre à jour la réponse existante
            result = QuizAttemptModel.get_collection().update_one(
                {"_id": ObjectId(attempt_id)},
                {"$set": {f"answers.{existing_answer_index}": answer}}
            )
        else:
            # Ajouter une nouvelle réponse
            result = QuizAttemptModel.get_collection().update_one(
                {"_id": ObjectId(attempt_id)},
                {"$push": {"answers": answer}}
            )
        
        return result.modified_count > 0
    
    @staticmethod
    def submit_attempt(attempt_id, answers, time_spent):
        """
        Soumet une tentative et calcule le score.
        """
        result = QuizAttemptModel.get_collection().update_one(
            {"_id": ObjectId(attempt_id)},
            {
                "$set": {
                    "status": "completed",
                    "submitted_at": datetime.utcnow(),
                    "time_spent_seconds": time_spent,
                    "answers": answers
                }
            }
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def abandon_attempt(attempt_id):
        """
        Abandonne une tentative.
        """
        result = QuizAttemptModel.get_collection().update_one(
            {"_id": ObjectId(attempt_id)},
            {"$set": {"status": "abandoned"}}
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def get_best_attempt(user_id, quiz_id):
        """
        Récupère la meilleure tentative d'un utilisateur pour un quiz.
        """
        attempt = QuizAttemptModel.get_collection().find_one(
            {
                "user_id": ObjectId(user_id),
                "quiz_id": ObjectId(quiz_id),
                "status": "completed"
            },
            sort=[("score", -1)]
        )
        return attempt
    
    @staticmethod
    def get_user_stats(user_id, church_id):
        """
        Récupère les statistiques d'un utilisateur.
        """
        pipeline = [
            {"$match": {
                "user_id": ObjectId(user_id),
                "church_id": ObjectId(church_id),
                "status": "completed"
            }},
            {"$group": {
                "_id": None,
                "total_attempts": {"$sum": 1},
                "passed_attempts": {
                    "$sum": {"$cond": ["$passed", 1, 0]}
                },
                "avg_score": {"$avg": "$score"},
                "total_time": {"$sum": "$time_spent_seconds"}
            }}
        ]
        
        result = list(QuizAttemptModel.get_collection().aggregate(pipeline))
        return result[0] if result else None