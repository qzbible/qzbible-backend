# schemas/catalog_schema.py

from marshmallow import Schema, fields, validate, validates_schema, ValidationError

class CatalogPreviewSchema(Schema):
    """Schema pour l'aperçu du contenu"""
    chapters_count = fields.Integer(required=False, missing=0)
    quiz_count = fields.Integer(required=False, missing=0)
    avg_rating = fields.Float(required=False, missing=0)


class PublishToCatalogSchema(Schema):
    """Schema pour publier du contenu au catalogue"""
    content_type = fields.String(
        required=True,
        validate=validate.OneOf(["section", "chapter", "quiz"]),
        error_messages={"required": "Le type de contenu est requis"}
    )
    content_id = fields.String(
        required=True,
        error_messages={"required": "L'ID du contenu est requis"}
    )
    tags = fields.List(
        fields.String(),
        required=False,
        validate=validate.Length(max=10),
        missing=[]
    )


class CatalogFilterSchema(Schema):
    """Schema pour filtrer le catalogue"""
    content_type = fields.String(
        required=False,
        validate=validate.OneOf(["section", "chapter", "quiz"])
    )
    tags = fields.List(fields.String(), required=False)
    min_rating = fields.Float(required=False, validate=validate.Range(min=0, max=5))
    search = fields.String(required=False, validate=validate.Length(max=100))
    sort_by = fields.String(
        required=False,
        validate=validate.OneOf(["downloads", "rating", "recent"]),
        missing="downloads"
    )


class RateCatalogItemSchema(Schema):
    """Schema pour noter un élément du catalogue"""
    rating = fields.Float(
        required=True,
        validate=validate.Range(min=1, max=5),
        error_messages={"required": "La note est requise"}
    )
    comment = fields.String(
        required=False,
        validate=validate.Length(max=500)
    )


class ImportFromCatalogSchema(Schema):
    """Schema pour importer depuis le catalogue"""
    catalog_item_id = fields.String(
        required=True,
        error_messages={"required": "L'ID de l'élément du catalogue est requis"}
    )
    target_section_id = fields.String(
        required=False,
        allow_none=True
    )