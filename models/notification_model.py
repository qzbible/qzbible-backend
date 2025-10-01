# models/notitifaction_model.py

from datetime import datetime
from bson import ObjectId
from extensions import mongo



class NotificationModel:
    @staticmethod
    def get_collection():
        return mongo.db.notifications

    @staticmethod
    def create_notification(data):
        """
        Crée une nouvelle notification.
        """
        notification = {
            "title": data["title"],
            "message": data["message"],
            "type": data.get("type", "info"),
            "lien": data.get("lien"),
            "timestamp": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "vu": False
        }
        
        result = NotificationModel.get_collection().insert_one(notification)
        return str(result.inserted_id)

    @staticmethod
    def get_notifications():
        """
        Récupère toutes les notifications dont vu est à False.
        """
        notifications = NotificationModel.get_collection().find({"vu": False}).sort("created_at", -1)
        return [{"id": str(n["_id"]), "title": n["title"], "message": n["message"], "created_at": n["created_at"].isoformat()} for n in notifications]

    @staticmethod
    def marquer_comme_vu(notification_id):
        """
        Marque une notification comme vue.
        """
        result = NotificationModel.get_collection().update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"vu": True}}
        )
        return result.modified_count > 0