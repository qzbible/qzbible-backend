# schemas/manual_unlock_schema.py

from marshmallow import Schema, fields, validate

class CreateManualUnlockSchema(Schema):
    """Schema pour créer un déblocage manuel"""
    learner_id = fields.String(
        required=True,
        error_messages={"required": "L'ID de l'apprenant est requis"}
    )
    chapter_id = fields.String(
        required=True,
        error_messages={"required": "L'ID du chapitre est requis"}
    )
    reason = fields.String(
        required=False,
        validate=validate.Length(max=500),
        missing="Déblocage manuel par le leader"
    )


class ManualUnlockFilterSchema(Schema):
    """Schema pour filtrer les déblocages manuels"""
    learner_id = fields.String(required=False)
    chapter_id = fields.String(required=False)
    unlocked_by = fields.String(required=False)
    start_date = fields.DateTime(required=False)
    end_date = fields.DateTime(required=False)