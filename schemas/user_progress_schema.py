# schemas/user_progress_schema.py

from marshmallow import Schema, fields, validate

class QuizProgressSchema(Schema):
    """Schema pour la progression sur un quiz"""
    quiz_id = fields.String(required=True)
    attempts_count = fields.Integer(required=False, missing=0)
    best_score = fields.Float(required=False, missing=0)
    best_attempt_id = fields.String(required=False, allow_none=True)
    last_attempt_at = fields.DateTime(required=False, allow_none=True)
    status = fields.String(
        required=False,
        validate=validate.OneOf(["not_attempted", "failed", "passed"]),
        missing="not_attempted"
    )


class ChapterProgressSchema(Schema):
    """Schema pour la progression sur un chapitre"""
    chapter_id = fields.String(required=True)
    status = fields.String(
        required=False,
        validate=validate.OneOf(["not_started", "in_progress", "completed"]),
        missing="not_started"
    )
    is_unlocked = fields.Boolean(required=False, missing=False)
    unlocked_at = fields.DateTime(required=False, allow_none=True)
    unlocked_by = fields.String(required=False, allow_none=True)
    quizzes_progress = fields.List(fields.Nested(QuizProgressSchema), required=False)
    completion_percentage = fields.Float(required=False, missing=0)
    avg_score = fields.Float(required=False, missing=0)


class SectionProgressSchema(Schema):
    """Schema pour la progression sur une section"""
    section_id = fields.String(required=True)
    status = fields.String(
        required=False,
        validate=validate.OneOf(["not_started", "in_progress", "completed"]),
        missing="not_started"
    )
    started_at = fields.DateTime(required=False, allow_none=True)
    completed_at = fields.DateTime(required=False, allow_none=True)
    chapters_progress = fields.List(fields.Nested(ChapterProgressSchema), required=False)
    completion_percentage = fields.Float(required=False, missing=0)
    total_time_spent_seconds = fields.Integer(required=False, missing=0)


class ManualUnlockSchema(Schema):
    """Schema pour débloquer manuellement un chapitre"""
    user_id = fields.String(
        required=True,
        error_messages={"required": "L'ID de l'utilisateur est requis"}
    )
    chapter_id = fields.String(
        required=True,
        error_messages={"required": "L'ID du chapitre est requis"}
    )
    reason = fields.String(required=False)