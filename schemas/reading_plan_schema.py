# schemas/simple_reading_plan_schema.py

from marshmallow import Schema, fields, validate

class ReadingScheduleItemSchema(Schema):
    """Schema pour un élément du planning de lecture"""
    day = fields.Integer(required=True, validate=validate.Range(min=1))
    label = fields.String(required=True)
    passages = fields.List(fields.String(), required=True)
    estimated_time = fields.Integer(required=True, validate=validate.Range(min=1))

class CreateSimplePlanSchema(Schema):
    """Schema pour créer un plan simple"""
    title = fields.String(required=True, validate=validate.Length(min=3, max=100))
    subtitle = fields.String(required=True, validate=validate.Length(min=3, max=200))
    description = fields.String(required=True, validate=validate.Length(max=500))
    duration_months = fields.Integer(required=True, validate=validate.Range(min=1, max=12))
    daily_chapters = fields.Integer(required=True, validate=validate.Range(min=1, max=10))
    book_focus = fields.List(fields.String(), required=True, validate=validate.Length(min=1))
    reading_schedule = fields.List(fields.Nested(ReadingScheduleItemSchema), required=True)
    emoji = fields.String(required=False, missing="📖")
    color = fields.String(required=False, missing="#2196F3")

class SubscribeSimplePlanSchema(Schema):
    """Schema pour s'inscrire à un plan simple"""
    plan_id = fields.String(required=True)
    reminder_time = fields.String(required=False, missing="07:00")
    reminder_enabled = fields.Boolean(required=False, missing=True)

class MarkDayCompletedSchema(Schema):
    """Schema pour marquer un jour comme complété"""
    day = fields.Integer(required=True, validate=validate.Range(min=1))