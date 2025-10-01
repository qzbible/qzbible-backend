# schemas/commande_schema.py

from marshmallow import Schema, fields
from marshmallow.validate import OneOf

class ProduitCommandeSchema(Schema):
    produit_id = fields.String(required=True, description="ID du produit commandé")
    nom = fields.String(required=True, description="Nom du produit")
    quantite = fields.Integer(required=True, description="Quantité commandée")
    prix = fields.Float(required=True, description="Prix unitaire")

class CreateCommandeSchema(Schema):
    client_id = fields.String(required=True, description="ID du client")
    magasin_id = fields.String(required=True, description="ID du magasin")
    produits = fields.List(fields.Nested(ProduitCommandeSchema), required=True, description="Liste des produits commandés")
    montant_total = fields.Float(required=True, description="Montant total de la commande")
    statut = fields.String(
        required=False,
        validate=OneOf(["en_attente", "validée", "livrée", "annulée"]),
        missing="en_attente",
        description="Statut de la commande"
    )
    adresse_livraison = fields.String(required=True, description="Adresse de livraison")
    date_commande = fields.DateTime(dump_only=True, description="Date de création de la commande")
    created_at = fields.DateTime(dump_only=True, description="Date d'enregistrement")
    updated_at = fields.DateTime(dump_only=True, description="Dernière mise à jour")


class UpdateCommandeSchema(Schema):
    client_id = fields.String(description="ID du client")
    magasin_id = fields.String(description="ID du magasin")
    produits = fields.List(fields.Nested(ProduitCommandeSchema), description="Liste des produits commandés")
    montant_total = fields.Float(description="Montant total de la commande")
    statut = fields.String(
        validate=OneOf(["en_attente", "validée", "livrée", "annulée"]),
        description="Statut de la commande"
    )
    adresse_livraison = fields.String(description="Adresse de livraison")
    date_commande = fields.DateTime(dump_only=True, description="Date de création de la commande")
    created_at = fields.DateTime(dump_only=True, description="Date d'enregistrement")
    updated_at = fields.DateTime(dump_only=True, description="Dernière mise à jour")