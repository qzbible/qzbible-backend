# scripts/corriger_conditionnements.py

from bson import ObjectId
from app import create_app
from models.produit_model import ProduitModel

def corriger_conditionnements_sans_id():
    app = create_app()
    with app.app_context():
        produits = ProduitModel.get_collection().find({
            "conditionnements": {"$exists": True}
        })

        count_total = 0
        count_modifies = 0

        for produit in produits:
            conditionnements = produit.get("conditionnements", [])
            if not conditionnements:
                continue  # ❗ Laisser intact les produits sans conditionnements

            updated = False
            for cond in conditionnements:
                if "_id" not in cond:
                    cond["_id"] = ObjectId()
                    updated = True

            if updated:
                ProduitModel.get_collection().update_one(
                    {"_id": produit["_id"]},
                    {"$set": {"conditionnements": conditionnements}}
                )
                count_modifies += 1
            count_total += 1

        print(f"✅ Produits parcourus : {count_total}")
        print(f"🔧 Produits corrigés (ajout d'ID dans conditionnements) : {count_modifies}")

if __name__ == "__main__":
    corriger_conditionnements_sans_id()
