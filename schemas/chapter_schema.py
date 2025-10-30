# schemas/chapter_schema.py

from marshmallow import Schema, fields, validate, validates_schema, ValidationError

class ResourceSchema(Schema):
    """Schema pour une ressource pédagogique"""
    type = fields.String(
        required=True,
        validate=validate.OneOf(["video", "pdf", "audio", "link", "image"]),
        error_messages={"required": "Le type de ressource est requis"}
    )
    url = fields.String(required=True)
    title = fields.String(required=True)


class UnlockRequirementsSchema(Schema):
    """Schema pour les conditions de déblocage"""
    previous_chapter_id = fields.String(required=False, allow_none=True)
    min_score = fields.Integer(
        required=False,
        validate=validate.Range(min=0, max=100),
        missing=70
    )
    completion_required = fields.Boolean(required=False, missing=True)


class ContentSchema(Schema):
    """Schema pour le contenu pédagogique"""
    introduction = fields.String(required=False, allow_none=True)
    resources = fields.List(fields.Nested(ResourceSchema), required=False)


class CreateChapterSchema(Schema):
    section_id = fields.String(
        required=True,
        error_messages={"required": "L'ID de la section est requis"}
    )
    title = fields.String(
        required=True,
        validate=validate.Length(min=3, max=200),
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
    content = fields.Nested(ContentSchema, required=False)
    unlock_requirements = fields.Nested(UnlockRequirementsSchema, required=False)
    church_id = fields.String(required=True)
    created_by = fields.String(required=True, load_only=True)


class UpdateChapterSchema(Schema):
    title = fields.String(
        validate=validate.Length(min=3, max=200)
    )
    description = fields.String(
        validate=validate.Length(max=2000)
    )
    order = fields.Integer(
        validate=validate.Range(min=1)
    )
    content = fields.Nested(ContentSchema, required=False)
    unlock_requirements = fields.Nested(UnlockRequirementsSchema, required=False)
    
    @validates_schema
    def validate_order(self, data, **kwargs):
        """Validation personnalisée si nécessaire"""
        pass