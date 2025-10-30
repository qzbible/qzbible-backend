# schemas/quiz_schema.py

from marshmallow import Schema, fields, validate, validates_schema, ValidationError

class MediaSchema(Schema):
    """Schema pour les médias associés aux questions"""
    type = fields.String(
        required=True,
        validate=validate.OneOf(["image", "audio", "video"]),
        error_messages={"required": "Le type de média est requis"}
    )
    url = fields.String(required=True)


class OptionSchema(Schema):
    """Schema pour une option de QCM"""
    text = fields.String(required=True)
    is_correct = fields.Boolean(required=True)
    points = fields.Integer(
        required=False,
        validate=validate.Range(min=0),
        missing=0
    )


class QuestionSchema(Schema):
    """Schema pour une question"""
    type = fields.String(
        required=True,
        validate=validate.OneOf([
            "mcq_single",      # QCM à choix unique
            "mcq_multiple",    # QCM à choix multiples
            "true_false",      # Vrai/Faux
            "fill_blank",      # Compléter la phrase
            "free_text"        # Réponse libre
        ]),
        error_messages={"required": "Le type de question est requis"}
    )
    order = fields.Integer(
        required=True,
        validate=validate.Range(min=1)
    )
    question_text = fields.String(
        required=True,
        validate=validate.Length(min=5, max=1000),
        error_messages={"required": "Le texte de la question est requis"}
    )
    points = fields.Integer(
        required=True,
        validate=validate.Range(min=1, max=100),
        error_messages={"required": "Les points sont requis"}
    )
    
    # Pour QCM
    options = fields.List(
        fields.Nested(OptionSchema),
        required=False
    )
    
    # Pour compléter la phrase
    fill_blank_text = fields.String(required=False)
    correct_answers = fields.List(fields.String(), required=False)
    
    # Pour réponse libre
    free_text_answers = fields.List(fields.String(), required=False)
    case_sensitive = fields.Boolean(required=False, missing=False)
    
    # Optionnels
    explanation = fields.String(required=False)
    media = fields.Nested(MediaSchema, required=False)
    
    @validates_schema
    def validate_question_type(self, data, **kwargs):
        """Valide que les champs requis sont présents selon le type"""
        question_type = data.get("type")
        
        if question_type in ["mcq_single", "mcq_multiple", "true_false"]:
            if not data.get("options") or len(data["options"]) < 2:
                raise ValidationError("Au moins 2 options sont requises pour ce type de question")
        
        if question_type == "fill_blank":
            if not data.get("fill_blank_text"):
                raise ValidationError("fill_blank_text est requis pour ce type de question")
            if not data.get("correct_answers"):
                raise ValidationError("correct_answers est requis pour ce type de question")
        
        if question_type == "free_text":
            if not data.get("free_text_answers"):
                raise ValidationError("free_text_answers est requis pour ce type de question")


class QuizSettingsSchema(Schema):
    """Schema pour les paramètres du quiz"""
    time_limit_minutes = fields.Integer(
        required=False,
        validate=validate.Range(min=1, max=240),
        missing=30
    )
    pass_score = fields.Integer(
        required=False,
        validate=validate.Range(min=0, max=100),
        missing=70
    )
    shuffle_questions = fields.Boolean(required=False, missing=True)
    shuffle_options = fields.Boolean(required=False, missing=True)
    show_correct_answers = fields.Boolean(required=False, missing=True)
    max_attempts = fields.Integer(
        required=False,
        validate=validate.Range(min=0),
        missing=0
    )
    allow_review = fields.Boolean(required=False, missing=True)


class CreateQuizSchema(Schema):
    chapter_id = fields.String(
        required=True,
        error_messages={"required": "L'ID du chapitre est requis"}
    )
    title = fields.String(
        required=True,
        validate=validate.Length(min=5, max=200),
        error_messages={"required": "Le titre est requis"}
    )
    description = fields.String(
        required=False,
        validate=validate.Length(max=2000)
    )
    order = fields.Integer(
        required=False,
        validate=validate.Range(min=1)
    )
    settings = fields.Nested(QuizSettingsSchema, required=False)
    questions = fields.List(
        fields.Nested(QuestionSchema),
        required=True,
        validate=validate.Length(min=1),
        error_messages={"required": "Au moins une question est requise"}
    )
    church_id = fields.String(required=True)
    created_by = fields.String(required=True, load_only=True)


class UpdateQuizSchema(Schema):
    title = fields.String(
        validate=validate.Length(min=5, max=200)
    )
    description = fields.String(
        validate=validate.Length(max=2000)
    )
    order = fields.Integer(
        validate=validate.Range(min=1)
    )
    settings = fields.Nested(QuizSettingsSchema, required=False)
    questions = fields.List(
        fields.Nested(QuestionSchema),
        required=False
    )