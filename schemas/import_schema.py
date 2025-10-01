from marshmallow import Schema, fields, EXCLUDE

class ImportProduitSchema(Schema):
    class Meta:
        unknown = EXCLUDE 
        
    nom = fields.Str(required=True)
    description = fields.Str(required=False, allow_none=True)
    prix = fields.Float(required=True)
    unite = fields.Str(required=True)
    quantite = fields.Int(required=True)
    categorie = fields.Str(required=True)
