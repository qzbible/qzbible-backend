from flask import Blueprint, jsonify, request
 
from utils.decorators import role_required
 
 

from flask_jwt_extended import jwt_required, get_jwt_identity  
from utils.decorators import livreur_required

dashboard_bp = Blueprint("dashboard", __name__)
   
  
 