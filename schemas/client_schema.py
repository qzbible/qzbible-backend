from marshmallow import Schema, fields, validate

class CreateClientSchema(Schema):
    nom = fields.String(required=True, validate=validate.Length(min=2))
    telephone = fields.String(required=True, validate=validate.Length(min=8))
    email = fields.Email(required=False)
    ville = fields.String(required=True)
    quartier = fields.String(required=True)
    magasin_id = fields.String(required=True)
    photo_profil = fields.Raw(required=False, type="file")
    created_by = fields.String(required=True, load_only=True)  

class UpdateClientSchema(Schema):
    nom = fields.String(validate=validate.Length(min=2))
    telephone = fields.String(validate=validate.Length(min=8))
    email = fields.Email()
    ville = fields.String()
    quartier = fields.String()
    photo_profil = fields.Raw(required=False, type="file")
