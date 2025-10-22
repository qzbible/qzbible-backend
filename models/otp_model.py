# models/otp_model.py

from datetime import datetime, timedelta
from bson import ObjectId
from extensions import mongo
import secrets

class OTPModel:
    """
    Modèle pour gérer les codes OTP (One-Time Password)
    """
    
    @staticmethod
    def get_collection():
        """Récupère la collection OTP"""
        return mongo.db.otps
    
    @staticmethod
    def initialize_indexes():
        """
        Initialise les index de la collection OTP
        À appeler au démarrage de l'application
        """
        collection = OTPModel.get_collection()
        
        # Index TTL pour suppression automatique des OTP expirés
        collection.create_index("expires_at", expireAfterSeconds=0)
        
        # Index unique sur l'email
        collection.create_index("email", unique=True)
        
        print("✅ Index OTP créés avec succès")
    
    @staticmethod
    def generate_otp(length=6):
        """
        Génère un OTP sécurisé
        :param length: Longueur du code OTP (par défaut 6)
        :return: Code OTP sous forme de chaîne
        """
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    @staticmethod
    def create_otp(email, expiration_minutes=10):
        """
        Crée un nouveau OTP pour un email donné
        :param email: Email de l'utilisateur
        :param expiration_minutes: Durée de validité de l'OTP en minutes (par défaut 10)
        :return: Code OTP généré
        """
        code = OTPModel.generate_otp(6)
        expires_at = datetime.utcnow() + timedelta(minutes=expiration_minutes)
        
        otp_data = {
            "email": email.lower(),
            "code": code,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "attempts": 0,
            "is_verified": False
        }
        
        # Upsert : met à jour si existe, crée sinon
        OTPModel.get_collection().update_one(
            {"email": email.lower()},
            {"$set": otp_data},
            upsert=True
        )
        
        return code
    
    @staticmethod
    def find_by_email(email):
        """
        Recherche un OTP par email
        :param email: Email de l'utilisateur
        :return: Document OTP ou None
        """
        return OTPModel.get_collection().find_one({"email": email.lower()})
    
    @staticmethod
    def verify_otp(email, code):
        """
        Vérifie un code OTP
        :param email: Email de l'utilisateur
        :param code: Code OTP à vérifier
        :return: Dictionnaire avec success (bool) et message (str)
        """
        otp = OTPModel.find_by_email(email)
        
        if not otp:
            return {
                "success": False,
                "message": "Aucun code OTP trouvé pour cet email"
            }
        
        # Vérifier l'expiration
        if datetime.utcnow() > otp['expires_at']:
            OTPModel.delete_otp(email)
            return {
                "success": False,
                "message": "Le code OTP a expiré"
            }
        
        # Vérifier le nombre de tentatives
        if otp['attempts'] >= 3:
            OTPModel.delete_otp(email)
            return {
                "success": False,
                "message": "Nombre maximum de tentatives atteint. Demandez un nouveau code."
            }
        
        # Vérifier le code
        if otp['code'] == code:
            # Marquer comme vérifié et supprimer
            OTPModel.get_collection().update_one(
                {"email": email.lower()},
                {"$set": {"is_verified": True}}
            )
            OTPModel.delete_otp(email)
            return {
                "success": True,
                "message": "Code OTP vérifié avec succès"
            }
        else:
            # Incrémenter le nombre de tentatives
            OTPModel.get_collection().update_one(
                {"email": email.lower()},
                {"$inc": {"attempts": 1}}
            )
            return {
                "success": False,
                "message": "Code OTP incorrect",
                "attempts_remaining": 3 - (otp['attempts'] + 1)
            }
    
    @staticmethod
    def is_valid(email):
        """
        Vérifie si un OTP valide existe pour un email
        :param email: Email de l'utilisateur
        :return: True si l'OTP est valide, False sinon
        """
        otp = OTPModel.find_by_email(email)
        
        if not otp:
            return False
        
        # Vérifier si non expiré
        if datetime.utcnow() > otp['expires_at']:
            OTPModel.delete_otp(email)
            return False
        
        return True
    
    @staticmethod
    def delete_otp(email):
        """
        Supprime un OTP par email
        :param email: Email de l'utilisateur
        :return: True si supprimé, False sinon
        """
        result = OTPModel.get_collection().delete_one({"email": email.lower()})
        return result.deleted_count > 0
    
    @staticmethod
    def get_otp_info(email):
        """
        Récupère les informations d'un OTP (pour debug ou statut)
        :param email: Email de l'utilisateur
        :return: Dictionnaire avec les informations de l'OTP ou None
        """
        otp = OTPModel.find_by_email(email)
        
        if not otp:
            return None
        
        # Vérifier si expiré
        is_expired = datetime.utcnow() > otp['expires_at']
        
        if is_expired:
            OTPModel.delete_otp(email)
            return None
        
        # Calculer le temps restant
        time_remaining = int((otp['expires_at'] - datetime.utcnow()).total_seconds())
        
        return {
            "email": otp['email'],
            "created_at": otp['created_at'],
            "expires_at": otp['expires_at'],
            "time_remaining_seconds": time_remaining,
            "attempts": otp['attempts'],
            "attempts_remaining": 3 - otp['attempts'],
            "is_verified": otp.get('is_verified', False)
        }
    
    @staticmethod
    def cleanup_expired():
        """
        Nettoie manuellement tous les OTP expirés
        (Normalement géré automatiquement par l'index TTL)
        :return: Nombre d'OTP supprimés
        """
        result = OTPModel.get_collection().delete_many({
            "expires_at": {"$lt": datetime.utcnow()}
        })
        return result.deleted_count