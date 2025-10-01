# schemas/categorie_schema.py

from marshmallow import Schema, fields

class CreateCategorieSchema(Schema):
    nom = fields.String(required=True)
    description = fields.String(required=False)
    magasin_id = fields.String(required=True)  # à valider côté route

class UpdateCategorieSchema(Schema):
    nom = fields.String()
    description = fields.String()
