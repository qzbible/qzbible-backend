# schemas/church_schema.py

from marshmallow import Schema, fields, validate


class LicenceSchema(Schema):
    max_managers = fields.Int(required=True, validate=validate.Range(min=1))
    max_livreurs = fields.Int(required=True, validate=validate.Range(min=1))


class CreateChurchSchema(Schema):
    denomination = fields.String(required=True, validate=validate.Length(min=3))
    pays = fields.String(required=True)
    logo = fields.String(required=False)
    ville = fields.String(required=True)
    quartier = fields.String(required=True)
    email = fields.Email(required=True)
    activité = fields.String(required=True)
    nombre_manager = fields.Int(required=True, validate=validate.Range(min=1))
    nombre_livreur = fields.Int(required=True, validate=validate.Range(min=1))
    # information sur l'admin
    admin = fields.Dict(required=True, keys=fields.String(), values=fields.String())
    #licence = fields.Nested(LicenceSchema, required=True)

class ChurchUpdateSchema(Schema):
    denomination = fields.String(required=False)
    pays = fields.String(required=False)
    ville = fields.String(required=False)
    quartier = fields.String(required=False)
    email = fields.Email(required=False)
    activité = fields.String(required=False)
    licence = fields.Nested(LicenceSchema, required=False)
    
