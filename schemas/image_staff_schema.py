from marshmallow import Schema, fields, validate


class ImageStaffSchema(Schema):
    """
    Schema for validating staff image upload requests.
    """
    nom = fields.Str(required=True)
    description = fields.Str(required=False)
    categorie = fields.Str(required=False)
    tags = fields.List(fields.Str(), required=False)
    #filename = fields.Str(required=True)
    