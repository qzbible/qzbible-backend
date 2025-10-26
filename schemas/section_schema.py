from marshmallow import Schema, fields, validate

class CreateSectionSchema(Schema):
    title = fields.String(
        required=True, 
        validate=validate.Length(min=3, max=200),
        error_messages={"required": "Le titre est requis"}
    )
    description = fields.String(
        required=False,
        validate=validate.Length(max=1000)
    )
    order = fields.Integer(
        required=False,
        validate=validate.Range(min=1)
    )
    is_sequential = fields.Boolean(required=False, missing=True)
    icon = fields.Raw(required=False, type="file")
    church_id = fields.String(required=True)
    created_by = fields.String(required=True, load_only=True)


class UpdateSectionSchema(Schema):
    title = fields.String(
        validate=validate.Length(min=3, max=200)
    )
    description = fields.String(
        validate=validate.Length(max=1000)
    )
    order = fields.Integer(
        validate=validate.Range(min=1)
    )
    is_sequential = fields.Boolean()
    icon = fields.Raw(required=False, type="file")