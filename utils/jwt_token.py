# utils/jwt_token.py

import jwt
from datetime import datetime, timedelta
from flask import current_app


def generate_validation_token(user_id, expires_in=None):
    """
    Génère un token JWT pour validation d'email.

    :param user_id: ID de l'utilisateur
    :param expires_in: Durée de vie du token en secondes (optionnelle)
    :return: token JWT
    """
    if expires_in is None:
        expires_in = current_app.config["VALIDATION_TOKEN_EXPIRES"]

    payload = {
        "user_id": str(user_id),
        "exp": datetime.utcnow() + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
    return token


def decode_validation_token(token):
    """
    Décode le token JWT pour récupérer l'ID de l'utilisateur.

    :param token: JWT à décoder
    :return: user_id si succès, sinon une exception est levée
    """
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise Exception("Le lien de validation a expiré.")
    except jwt.InvalidTokenError:
        raise Exception("Token invalide.")



# utils/jwt_utils.py
from flask_jwt_extended import create_access_token

def generate_token(user_id, role):
    return create_access_token(identity=user_id, additional_claims={"role": role})
