# schemas/simple_reading_plan_schema.py

from marshmallow import Schema, fields, validate


# ✅ Définir d'abord ReadingScheduleItemSchema
class ReadingScheduleItemSchema(Schema):
    """Schema pour un élément du planning de lecture"""
    day = fields.Integer(required=True, validate=validate.Range(min=1))
    label = fields.String(required=True)
    passages = fields.List(fields.String(), required=True)
    estimated_time = fields.Integer(required=True, validate=validate.Range(min=1))

class NotificationRecurrenceSchema(Schema):
    """Schema pour la récurrence des notifications"""
    type = fields.String(validate=validate.OneOf(["daily", "weekly", "monthly", "yearly"]), missing="daily")
    interval = fields.Integer(validate=validate.Range(min=1), missing=1)
    days_of_week = fields.List(fields.Integer(validate=validate.Range(min=0, max=6)), missing=[])
    day_of_month = fields.Integer(validate=validate.Range(min=1, max=31), allow_none=True)
    end_condition = fields.Dict(missing={
        "type": "never",
        "end_date": None,
        "occurrences": None
    })

class NotificationSettingsSchema(Schema):
    """Schema pour les paramètres de notification"""
    enabled = fields.Boolean(missing=True)
    default_time = fields.String(missing="07:00")
    frequency = fields.String(validate=validate.OneOf(["daily", "weekly", "monthly"]), missing="daily")
    recurrence_pattern = fields.Nested(NotificationRecurrenceSchema, missing={})
    reminder_types = fields.List(fields.String(validate=validate.OneOf(["notification", "email", "sms"])), missing=["notification"])
    advance_reminders = fields.List(fields.Dict(), missing=[])
    custom_message = fields.String(allow_none=True)

class UserNotificationPreferencesSchema(Schema):
    """Schema pour les préférences utilisateur"""
    enabled = fields.Boolean(missing=True)
    reminder_time = fields.String(missing="07:00")
    frequency = fields.String(validate=validate.OneOf(["daily", "weekly", "custom"]), missing="daily")
    days_of_week = fields.List(fields.Integer(validate=validate.Range(min=0, max=6)), missing=[0,1,2,3,4,5,6])
    recurrence = fields.Dict(missing={"type": "daily", "interval": 1})
    advance_reminders = fields.List(fields.Dict(), missing=[])
    reminder_types = fields.List(fields.String(), missing=["push"])
    custom_message = fields.String(allow_none=True)
    snooze_options = fields.List(fields.Integer(), missing=[5, 15, 30, 60])
    quiet_hours = fields.Dict(missing={"enabled": False, "start_time": "22:00", "end_time": "06:00"})

# ✅ Maintenant on peut utiliser ReadingScheduleItemSchema
class CreateSimplePlanSchema(Schema):
    """Schema pour créer un plan simple avec notifications"""
    title = fields.String(required=True, validate=validate.Length(min=3, max=100))
    subtitle = fields.String(required=True, validate=validate.Length(min=3, max=200))
    description = fields.String(required=True, validate=validate.Length(max=500))
    duration_months = fields.Integer(required=True, validate=validate.Range(min=1, max=12))
    daily_chapters = fields.Integer(required=True, validate=validate.Range(min=1, max=10))
    book_focus = fields.List(fields.String(), required=True, validate=validate.Length(min=1))
    reading_schedule = fields.List(fields.Nested(ReadingScheduleItemSchema), required=True)
    emoji = fields.String(required=False, missing="📖")
    color = fields.String(required=False, missing="#2196F3")
    has_notifications = fields.Boolean(required=False, missing=True)
    auto_save_progress = fields.Boolean(required=False, missing=True)
    is_template = fields.Boolean(required=False, missing=False)
    notification_settings = fields.Nested(NotificationSettingsSchema, missing={})

class SubscribeSimplePlanSchema(Schema):
    """Schema pour s'inscrire avec préférences de notification"""
    reminder_time = fields.String(required=False, missing="07:00")
    reminder_enabled = fields.Boolean(required=False, missing=True)
    notification_preferences = fields.Nested(UserNotificationPreferencesSchema, missing={})

class MarkDayCompletedSchema(Schema):
    """Schema pour marquer un jour comme complété"""
    day = fields.Integer(required=True, validate=validate.Range(min=1))