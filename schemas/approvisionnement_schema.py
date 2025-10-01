# schemas/approvisionnement_schema.py

from marshmallow import Schema, fields, validate

class ProduitApproSchema(Schema):
    produit_id = fields.Str(required=True, validate=validate.Length(equal=24))
    quantite = fields.Int(required=True, validate=validate.Range(min=1))

class ApprovisionnementSchema(Schema):
    magasin_id = fields.Str(required=True, validate=validate.Length(equal=24))
    admin_id = fields.Str(required=True, validate=validate.Length(equal=24))  # ou manager_id
    livreur_id = fields.Str(required=True, validate=validate.Length(equal=24))
    produits = fields.List(fields.Nested(ProduitApproSchema), required=True)
