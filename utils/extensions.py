# extensions.py

from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_mail import Mail

mongo = PyMongo()
jwt = JWTManager()
mail = Mail()
