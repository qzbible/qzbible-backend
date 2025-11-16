# schemas/reading_plan_schema.py

from marshmallow import Schema, fields, validate, validates_schema, ValidationError

class ContentRefSchema(Schema):
    """Schema pour les références de contenu"""
    type = fields.String(
        required=True,
        validate=validate.OneOf(['bible_passage', 'document_section', 'video', 'audio', 'article'])
    )
    resource_id = fields.String(required=True)
    specific_ref = fields.String(required=True)
    page_ref = fields.String(required=False, allow_none=True)
    display_ref = fields.String(required=True)

class ContentItemSchema(Schema):
    """Schema pour les éléments de contenu"""
    item_id = fields.String(required=True)
    day = fields.Integer(required=True, validate=validate.Range(min=1))
    order = fields.Integer(required=True, validate=validate.Range(min=1))
    content_type = fields.String(required=True)
    content_ref = fields.Nested(ContentRefSchema, required=True)
    title = fields.String(required=True)
    estimated_time = fields.Integer(required=True, validate=validate.Range(min=1))
    is_optional = fields.Boolean(required=False, missing=False)
    notes = fields.String(required=False, allow_none=True)

class CreateReadingPlanSchema(Schema):
    """Schema pour créer un plan de lecture"""
    title = fields.String(
        required=True,
        validate=validate.Length(min=3, max=200),
        error_messages={"required": "Le titre est requis"}
    )
    description = fields.String(
        required=False,
        validate=validate.Length(max=1000)
    )
    category = fields.String(
        required=True,
        validate=validate.OneOf(['bible', 'books', 'study', 'mixed']),
        error_messages={"required": "La catégorie est requise"}
    )
    visibility = fields.String(
        required=False,
        validate=validate.OneOf(['public', 'private', 'church_only']),
        missing='private'
    )
    duration_days = fields.Integer(
        required=True,
        validate=validate.Range(min=1, max=365),
        error_messages={"required": "La durée est requise"}
    )
    estimated_daily_time = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        error_messages={"required": "Le temps quotidien estimé est requis"}
    )
    difficulty_level = fields.String(
        required=False,
        validate=validate.OneOf(['beginner', 'intermediate', 'advanced']),
        missing='intermediate'
    )
    tags = fields.List(
        fields.String(),
        required=False,
        validate=validate.Length(max=10),
        missing=[]
    )
    content_items = fields.List(
        fields.Nested(ContentItemSchema),
        required=True,
        validate=validate.Length(min=1),
        error_messages={"required": "Au moins un élément de contenu est requis"}
    )
    quiz_integration = fields.Dict(required=False, missing={"has_quizzes": False})

class ReadingPlanFiltersSchema(Schema):
    """Schema pour filtrer les plans de lecture"""
    category = fields.String(
        required=False,
        validate=validate.OneOf(['bible', 'books', 'study', 'mixed'])
    )
    difficulty = fields.String(
        required=False,
        validate=validate.OneOf(['beginner', 'intermediate', 'advanced'])
    )
    creator_type = fields.String(
        required=False,
        validate=validate.OneOf(['admin', 'pastor', 'user'])
    )
    duration_range = fields.String(
        required=False,
        validate=validate.Regexp(r'^\d+-\d+$', error="Format requis: min-max (ex: 7-30)")
    )
    tags = fields.List(fields.String(), required=False)
    search = fields.String(required=False, validate=validate.Length(max=100))
    sort_by = fields.String(
        required=False,
        validate=validate.OneOf(['created_at', 'popular', 'rating']),
        missing='created_at'
    )

class CustomizationsSchema(Schema):
    """Schema pour les personnalisations utilisateur"""
    daily_reminder_time = fields.String(
        required=False,
        validate=validate.Regexp(r'^([01]\d|2[0-3]):([0-5]\d)$', error="Format requis: HH:MM"),
        missing='07:00'
    )
    reminder_days = fields.List(
        fields.String(validate=validate.OneOf([
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
        ])),
        required=False,
        missing=['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    )
    pace = fields.String(
        required=False,
        validate=validate.OneOf(['slow', 'normal', 'fast']),
        missing='normal'
    )
    bible_version = fields.String(required=False, missing='louis_segond')
    catch_up_mode = fields.String(
        required=False,
        validate=validate.OneOf(['extend_duration', 'compress_readings', 'skip_missed']),
        missing='extend_duration'
    )

class SubscribeToPlanSchema(Schema):
    """Schema pour s'inscrire à un plan"""
    plan_id = fields.String(
        required=True,
        error_messages={"required": "L'ID du plan est requis"}
    )
    customizations = fields.Nested(CustomizationsSchema, required=False, missing={})

class MarkProgressSchema(Schema):
    """Schema pour marquer la progression"""
    item_id = fields.String(
        required=True,
        error_messages={"required": "L'ID de l'élément est requis"}
    )
    completed = fields.Boolean(required=False, missing=True)
    time_spent = fields.Integer(required=False, validate=validate.Range(min=0), missing=0)
    notes = fields.String(required=False, validate=validate.Length(max=500))
    rating = fields.Integer(required=False, validate=validate.Range(min=1, max=5))

class CatchUpStrategySchema(Schema):
    """Schema pour les stratégies de rattrapage"""
    strategy = fields.String(
        required=True,
        validate=validate.OneOf(['extend_duration', 'compress_readings', 'skip_optional']),
        error_messages={"required": "La stratégie est requise"}
    )
    params = fields.Dict(required=False, missing={})

class QuickCreatePlanSchema(Schema):
    """Schema pour la création rapide de plan"""
    template_type = fields.String(
        required=True,
        validate=validate.OneOf(['document_study', 'bible_study', 'mixed_study']),
        error_messages={"required": "Le type de template est requis"}
    )
    source = fields.Dict(required=True)
    plan_info = fields.Dict(required=False, missing={})
    preferences = fields.Dict(required=False, missing={})

# Schémas pour les documents
class DocumentCreateSchema(Schema):
    """Schema pour créer un document"""
    title = fields.String(
        required=True,
        validate=validate.Length(min=2, max=200),
        error_messages={"required": "Le titre est requis"}
    )
    author = fields.String(
        required=True,
        validate=validate.Length(min=2, max=100),
        error_messages={"required": "L'auteur est requis"}
    )
    category = fields.String(
        required=True,
        validate=validate.OneOf(['theology', 'devotional', 'study', 'biography', 'commentary']),
        error_messages={"required": "La catégorie est requise"}
    )
    language = fields.String(
        required=False,
        validate=validate.OneOf(['fr', 'en']),
        missing='fr'
    )
    description = fields.String(required=False, validate=validate.Length(max=1000))
    tags = fields.List(fields.String(), required=False, missing=[])
    visibility = fields.String(
        required=False,
        validate=validate.OneOf(['public', 'church_only', 'private']),
        missing='public'
    )
    difficulty_level = fields.String(
        required=False,
        validate=validate.OneOf(['beginner', 'intermediate', 'advanced']),
        missing='intermediate'
    )

class DocumentStructureSchema(Schema):
    """Schema pour la structure d'un document"""
    total_pages = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        error_messages={"required": "Le nombre total de pages est requis"}
    )
    chapters = fields.List(fields.Dict(), required=False, missing=[])
    sections = fields.List(fields.Dict(), required=False, missing=[])

class DocumentFiltersSchema(Schema):
    """Schema pour filtrer les documents"""
    category = fields.String(
        required=False,
        validate=validate.OneOf(['theology', 'devotional', 'study', 'biography', 'commentary'])
    )
    language = fields.String(
        required=False,
        validate=validate.OneOf(['fr', 'en'])
    )
    has_page_numbers = fields.Boolean(required=False)
    min_pages = fields.Integer(required=False, validate=validate.Range(min=1))