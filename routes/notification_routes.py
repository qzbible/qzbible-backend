# routes/notification_routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user_model import UserModel
from models.notification_model import NotificationModel

notification_bp = Blueprint("notification", __name__)


@notification_bp.route("/notifications", methods=["GET"])
@jwt_required()
def lister_notifications():
    user = UserModel.get_user_by_id(get_jwt_identity())
    notifications = NotificationModel.get_notifications()
    if not notifications:
        return jsonify([])
    return jsonify(notifications)

@notification_bp.route("/notifications/<id>/vu", methods=["PATCH"])
@jwt_required()
def marquer_notification_vu(id):
    NotificationModel.marquer_comme_vu(id)
    return jsonify({"message": "Notification marquée comme lue."})