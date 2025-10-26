# utils/decorators.py

from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
from flask import jsonify
 

def staff_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "staff":
            return jsonify({"msg": "Accès réservé au staff"}), 403
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"msg": "Accès réservé aux admins"}), 403
        return fn(*args, **kwargs)
    return wrapper

def manager_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "manager":
            return jsonify({"msg": "Accès réservé aux managers"}), 403
        return fn(*args, **kwargs)
    return wrapper

def livreur_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "livreur":
            return jsonify({"msg": "Accès réservé aux livreurs"}), 403
        return fn(*args, **kwargs)
    return wrapper


def role_required(*roles):
    """
    Décorateur générique pour autoriser plusieurs rôles.
    Exemple : @role_required("admin", "staff", "livreur")
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role")

            if user_role not in roles:
                return jsonify({"msg": "Accès interdit pour le rôle actuel."}), 403

            return fn(*args, **kwargs)
        return decorated_view
    return wrapper



 