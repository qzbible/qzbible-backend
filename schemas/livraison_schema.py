# schemas/livraison_schema.py

from marshmallow import Schema, fields, validate
from datetime import datetime

class ConditionnementSchema(Schema):
    nom = fields.Str(required=True)
    quantite = fields.Int(required=True, validate=validate.Range(min=1))
    prix_conditionnement = fields.Float(required=False, validate=validate.Range(min=0))



class LivraisonSchema(Schema):
    manager_id = fields.Str(required=False, validate=validate.Length(equal=24))
    client_id = fields.Str(required=True, validate=validate.Length(equal=24))
    livreur_id = fields.Str(required=True, validate=validate.Length(equal=24))
    produits = fields.List(fields.Dict(), required=True)
    conditionnements = fields.List(fields.Nested(ConditionnementSchema), required=False, missing=[])
    statut_paiement = fields.Str(required=True, validate=validate.OneOf(["non payé", "payé", "partiellement payé"]))
    statut_livraison = fields.Str(required=False, default="en cours", validate=validate.OneOf(["en cours", "livrée", "annulée"]))
    date_commande = fields.DateTime(required=False ,default=datetime.utcnow)
    date_livraison = fields.DateTime(required=False)
    magasin_id = fields.Str(required=True, validate=validate.Length(equal=24))
    montant_paye = fields.Float(required=False, validate=validate.Range(min=0))
    relicat = fields.Float(required=False, validate=validate.Range(min=0))
    conditionnement = fields.Dict(required=False)
    retour = fields.Float(required=False, validate=validate.Range(min=0))
    ristourne = fields.Float(required=False, validate=validate.Range(min=0))    
    action_manager = fields.Boolean(required=False, default=False)
    class Meta:
        ordered = True


class LivraisonManagerSchema(Schema):
    manager_id = fields.Str(required=False, validate=validate.Length(equal=24))
    client_id = fields.Str(required=True, validate=validate.Length(equal=24))
    #livreur_id = fields.Str(required=True, validate=validate.Length(equal=24))
    produits = fields.List(fields.Dict(), required=True)
    conditionnements = fields.List(fields.Nested(ConditionnementSchema), required=False, missing=[])
    statut_paiement = fields.Str(required=True, validate=validate.OneOf(["non payé", "payé", "partiellement payé"]))
    statut_livraison = fields.Str(required=False, default="en cours", validate=validate.OneOf(["en cours", "livrée", "annulée"]))
    date_commande = fields.DateTime(required=False ,default=datetime.utcnow)
    date_livraison = fields.DateTime(required=False)
    magasin_id = fields.Str(required=True, validate=validate.Length(equal=24))
    montant_paye = fields.Float(required=False, validate=validate.Range(min=0))
    relicat = fields.Float(required=False, validate=validate.Range(min=0))
    retour = fields.Float(required=False, validate=validate.Range(min=0))
    ristourne = fields.Float(required=False, validate=validate.Range(min=0))    
    action_manager = fields.Boolean(required=False, default=False)
    class Meta:
        ordered = True
        


class RetourLivraisonSchema(Schema):
    livraison_id = fields.Str(required=True, validate=validate.Length(equal=24))
    produits = fields.List(fields.Dict(), required=True)  # liste de produits retournés
    motif = fields.Str(required=False)
    manager_id = fields.Str(validate=validate.Length(equal=24))
    livreur_id = fields.Str(validate=validate.Length(equal=24))
    created_at = fields.DateTime(dump_only=True, default=datetime.utcnow)

    class Meta:
        ordered = True