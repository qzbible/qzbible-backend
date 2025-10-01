import pandas as pd 
from schemas.import_schema import ImportProduitSchema
from models.produit_model import ProduitModel
from models.categorie_model import CategorieModel
from models.magasin_model import MagasinModel
from marshmallow import ValidationError



def import_produits_from_excel(fichier, magasin_id):
    try:
        df = pd.read_excel(fichier, engine='openpyxl')
    except Exception as e:
        return {"error": f"Erreur lors de la lecture du fichier Excel: {str(e)}"}, 400

    # Mappage des colonnes exportées → attendues
    column_mapping = {
        "Nom": "nom",
        "Description": "description",
        "Prix": "prix",
        "Unité": "unite",
        "Quantité": "quantite",
        "Catégorie": "categorie",
        "Image": "image",  # optionnel
    }

    # Renommer les colonnes si besoin
    df.rename(columns={col: column_mapping.get(col, col) for col in df.columns}, inplace=True)

    # Supprimer les colonnes non attendues
    colonnes_attendues = ["nom", "description", "prix", "unite", "quantite", "categorie", "conditionnements", "image"]
    df = df[[col for col in df.columns if col in colonnes_attendues]]

    # Ajouter une colonne vide pour conditionnements si absente
    if "conditionnements" not in df.columns:
        df["conditionnements"] = None

    schema = ImportProduitSchema()
    produits_crees = []
    erreurs = []

    def convert_type(val):
        if pd.isna(val):
            return None
        if isinstance(val, float):
            return float(val)
        if isinstance(val, int):
            return int(val)
        return str(val).strip()

    for index, ligne in df.iterrows():
        try:
            cleaned_data = {k: convert_type(v) for k, v in ligne.to_dict().items()}
            produit_data = schema.load(cleaned_data)
        except ValidationError as ve:
            erreurs.append(f"Ligne {index + 2} : Erreur de validation : {str(ve)}")
            continue
        except Exception as e:
            erreurs.append(f"Ligne {index + 2} : Erreur inconnue : {str(e)}")
            continue

        # Traitement de la catégorie
        categorie_id = CategorieModel.find_best_match(produit_data['categorie'])
        if not categorie_id:
            categorie_id = CategorieModel.create_if_not_exists(produit_data["categorie"])

        ProduitModel.create_from_excel(produit_data, magasin_id, categorie_id)
        produits_crees.append(produit_data['nom'])

    return {
        "message": "Importation terminée",
        "produits_crees": produits_crees,
        "erreurs": erreurs
    }, 201 if produits_crees else 400

