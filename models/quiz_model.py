# models/quiz_model.py

from bson import ObjectId
from datetime import datetime
from extensions import mongo

class QuizModel:
    
    collection = mongo.db.quizzes
    
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.quizzes
    
    @staticmethod
    def create_quiz(data):
        """
        Crée un nouveau quiz avec ses questions.
        
        :param data: dict contenant les informations du quiz
        :return: dict contenant le message de succès et l'ID du quiz créé
        """
        # Générer des ObjectId pour les questions et options
        for question in data.get("questions", []):
            question["_id"] = ObjectId()
            if "options" in question:
                for option in question["options"]:
                    option["_id"] = ObjectId()
        
        quiz = {
            "chapter_id": ObjectId(data["chapter_id"]),
            "church_id": ObjectId(data["church_id"]),
            "title": data["title"],
            "description": data.get("description", ""),
            "order": data.get("order", 1),
            "settings": data.get("settings", {
                "time_limit_minutes": 30,
                "pass_score": 70,
                "shuffle_questions": True,
                "shuffle_options": True,
                "show_correct_answers": True,
                "max_attempts": 0,
                "allow_review": True
            }),
            "questions": data.get("questions", []),
            "is_public": data.get("is_public", False),
            "source_quiz_id": ObjectId(data["source_quiz_id"]) if data.get("source_quiz_id") else None,
            "created_by": ObjectId(data["created_by"]) if data.get("created_by") else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = QuizModel.get_collection().insert_one(quiz)
        
        return {
            "message": "Quiz créé avec succès",
            "quiz_id": str(result.inserted_id)
        }
    
    @staticmethod
    def get_quiz_by_id(quiz_id):
        """
        Récupère un quiz par son ID avec toutes ses questions.
        """
        quiz = QuizModel.get_collection().find_one({"_id": ObjectId(quiz_id)})
        if quiz:
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
        
        return quiz
    
    @staticmethod
    def get_all_quizzes_by_chapter(chapter_id):
        """
        Récupère tous les quiz d'un chapitre donné.
        """
        quizzes = QuizModel.get_collection().find({
            "chapter_id": ObjectId(chapter_id)
        }).sort("order", 1)
        return list(quizzes)
    
    @staticmethod
    def get_all_quizzes_by_church(church_id):
        """
        Récupère tous les quiz d'une église.
        """
        quizzes = QuizModel.get_collection().find({
            "church_id": ObjectId(church_id)
        }).sort("order", 1)
        return list(quizzes)
    
    @staticmethod
    def update_quiz(quiz_id, data):
        """
        Met à jour les informations d'un quiz existant.
        """
        update_data = {k: data[k] for k in data if k in [
            "title", "description", "order", "settings", "questions"
        ]}
        update_data["updated_at"] = datetime.utcnow()
        
        # Générer des ObjectId pour les nouvelles questions et options
        if "questions" in update_data:
            for question in update_data["questions"]:
                if "_id" not in question or not question["_id"]:
                    question["_id"] = ObjectId()
                else:
                    # Convertir en ObjectId si c'est une chaîne
                    if isinstance(question["_id"], str):
                        question["_id"] = ObjectId(question["_id"])
                
                if "options" in question:
                    for option in question["options"]:
                        if "_id" not in option or not option["_id"]:
                            option["_id"] = ObjectId()
                        else:
                            if isinstance(option["_id"], str):
                                option["_id"] = ObjectId(option["_id"])
        
        result = QuizModel.get_collection().update_one(
            {"_id": ObjectId(quiz_id)},
            {"$set": update_data}
        )
        
        return {
            "message": "Quiz mis à jour avec succès",
            "modified_count": result.modified_count
        }
    
    @staticmethod
    def delete_quiz(quiz_id):
        """
        Supprime un quiz par son ID.
        """
        result = QuizModel.get_collection().delete_one({"_id": ObjectId(quiz_id)})
        
        return {
            "message": "Quiz supprimé avec succès",
            "deleted_count": result.deleted_count
        }
    
    @staticmethod
    def count_by_chapter(chapter_id):
        """
        Compte le nombre de quiz dans un chapitre.
        """
        return QuizModel.get_collection().count_documents({
            "chapter_id": ObjectId(chapter_id)
        })
    
    @staticmethod
    def get_next_order(chapter_id):
        """
        Obtient le prochain numéro d'ordre pour un nouveau quiz.
        """
        last_quiz = QuizModel.get_collection().find_one(
            {"chapter_id": ObjectId(chapter_id)},
            sort=[("order", -1)]
        )
        return (last_quiz["order"] + 1) if last_quiz else 1
    
    @staticmethod
    def calculate_total_points(quiz_id):
        """
        Calcule le total de points d'un quiz.
        """
        quiz = QuizModel.get_collection().find_one({"_id": ObjectId(quiz_id)})
        if not quiz:
            return 0
        
        total = sum(question.get("points", 0) for question in quiz.get("questions", []))
        return total
    
    @staticmethod
    def get_question_by_id(quiz_id, question_id):
        """
        Récupère une question spécifique d'un quiz.
        """
        quiz = QuizModel.get_collection().find_one({"_id": ObjectId(quiz_id)})
        if not quiz:
            return None
        
        for question in quiz.get("questions", []):
            if str(question["_id"]) == str(question_id):
                question["_id"] = str(question["_id"])
                if "options" in question:
                    for option in question["options"]:
                        option["_id"] = str(option["_id"])
                return question
        
        return None
    
    @staticmethod
    def count_attempts_by_quiz(quiz_id):
        """
        Compte le nombre de tentatives pour un quiz.
        """
        from models.quiz_attempt_model import QuizAttemptModel
        return QuizAttemptModel.get_collection().count_documents({
            "quiz_id": ObjectId(quiz_id)
        })