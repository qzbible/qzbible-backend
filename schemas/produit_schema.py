# schemas/produit_schema.py

from marshmallow import Schema, fields, validate


# Ajout de la classe ConditionnementSchema pour la validation des conditionnements
class ConditionnementSchema(Schema):
    nom = fields.String(required=True)
    facteur = fields.Integer(required=True, validate=validate.Range(min=1))
    prix_conditionnement = fields.Float(validate=validate.Range(min=0))  # optionnel

class ConditionnementUpdateSchema(Schema):
    _id = fields.String(required=False)  # Si fourni, indique une MAJ
    nom = fields.String(required=True)
    facteur = fields.Integer(required=True, validate=validate.Range(min=1))
    prix_conditionnement = fields.Float(validate=validate.Range(min=0))  # optionnel


class CreateProduitSchema(Schema):
    nom = fields.String(required=True)
    description = fields.String()
    prix = fields.Float(required=True, validate=validate.Range(min=0))
    quantite = fields.Integer(required=True, validate=validate.Range(min=0))
    categorie_id = fields.String(required=True)
    magasin_id = fields.String(required=False)
    unite = fields.String(required=True)
    image = fields.String()
    conditionnements = fields.List(fields.Nested(ConditionnementSchema()), required=False)
    admin_id = fields.String(required=False)  # ID de l'utilisateur qui crée le produit

    
    
class UpdateProduitSchema(Schema):
    nom = fields.String()
    description = fields.String()
    prix = fields.Float(validate=validate.Range(min=0))
    quantite = fields.Integer(required=False, validate=validate.Range(min=0))
    categorie_id = fields.String()
    unite = fields.String(required=False)
    image_url = fields.String()
    conditionnements = fields.List(fields.Nested(ConditionnementUpdateSchema()), required=False)
    admin_id = fields.String(required=False)  # ID de l'utilisateur qui met à jour le produit
