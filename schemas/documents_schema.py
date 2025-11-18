from marshmallow import Schema, fields, validate, validates_schema, ValidationError

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