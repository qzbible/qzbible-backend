from flask_jwt_extended import get_jwt_identity
from models.user_model import UserModel
from bson import ObjectId

def inject_magasin_id(data: dict) -> dict:
    current_user_id = get_jwt_identity()
    print(f"[DEBUG] JWT identity = {current_user_id}")

    try:
        user_id = ObjectId(current_user_id)
    except Exception as e:
        raise Exception(f"Échec de conversion de l'ID JWT en ObjectId : {e}")

    print(f"[DEBUG] Recherche utilisateur avec ObjectId({user_id})")

    user = UserModel.find_by_id(user_id)
    if not user:
        raise Exception("Utilisateur introuvable ou non authentifié.")

    magasin_id = user.get("magasin_id")
    if not magasin_id:
        raise Exception("Aucun magasin associé à cet utilisateur.")

    data["magasin_id"] = str(magasin_id)
    return data
