# schemas/quiz_attempt_schema.py

from marshmallow import Schema, fields, validate, validates_schema, ValidationError

class AnswerSchema(Schema):
    """Schema pour une réponse individuelle"""
    question_id = fields.String(
        required=True,
        error_messages={"required": "L'ID de la question est requis"}
    )
    question_type = fields.String(
        required=True,
        validate=validate.OneOf([
            "mcq_single", "mcq_multiple", "true_false", "fill_blank", "free_text"
        ])
    )
    
    # Pour QCM
    selected_options = fields.List(
        fields.String(),
        required=False
    )
    
    # Pour fill_blank
    fill_blank_answers = fields.List(
        fields.String(),
        required=False
    )
    
    # Pour free_text
    free_text_answer = fields.String(required=False, allow_none=True)
    
    # Calculés automatiquement par le backend
    is_correct = fields.Boolean(required=False)
    points_earned = fields.Integer(required=False)
    points_possible = fields.Integer(required=False)
    time_spent_seconds = fields.Integer(required=False)
    
    @validates_schema
    def validate_answer_type(self, data, **kwargs):
        """Valide que les champs requis sont présents selon le type"""
        question_type = data.get("question_type")
        
        if question_type in ["mcq_single", "mcq_multiple", "true_false"]:
            if not data.get("selected_options"):
                raise ValidationError("selected_options est requis pour ce type de question")
        
        if question_type == "fill_blank":
            if not data.get("fill_blank_answers"):
                raise ValidationError("fill_blank_answers est requis pour ce type de question")
        
        if question_type == "free_text":
            if data.get("free_text_answer") is None:
                raise ValidationError("free_text_answer est requis pour ce type de question")


class StartQuizAttemptSchema(Schema):
    """Schema pour démarrer une tentative"""
    quiz_id = fields.String(
        required=True,
        error_messages={"required": "L'ID du quiz est requis"}
    )


class SubmitQuizAttemptSchema(Schema):
    """Schema pour soumettre une tentative"""
    attempt_id = fields.String(
        required=True,
        error_messages={"required": "L'ID de la tentative est requis"}
    )
    answers = fields.List(
        fields.Nested(AnswerSchema),
        required=True,
        validate=validate.Length(min=1),
        error_messages={"required": "Les réponses sont requises"}
    )


class UpdateAnswerSchema(Schema):
    """Schema pour mettre à jour une réponse pendant la tentative"""
    attempt_id = fields.String(required=True)
    answer = fields.Nested(AnswerSchema, required=True)