from flask_jwt_extended import get_jwt_identity
from models.user_model import UserModel
from bson import ObjectId

def inject_church_id(data: dict) -> dict:
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

    church_id = user.get("church_id")
    if not church_id:
        raise Exception("Aucun church associé à cet utilisateur.")

    data["church_id"] = str(church_id)
    return data


def inject_church_id_with_email(data: dict, email:str) -> dict:
   
    user = UserModel.find_by_email(email)
    if not user:
        raise Exception("Utilisateur introuvable ou non authentifié.")

    church_id = user.get("church_id")
    if not church_id:
        raise Exception("Aucun church associé à cet utilisateur.")

    data["church_id"] = str(church_id)
    return data
