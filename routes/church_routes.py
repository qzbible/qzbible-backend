from flask import Blueprint, request, jsonify
import json
from flask_jwt_extended import jwt_required, get_jwt_identity
from schemas.church_schema import ChurchUpdateSchema, CreateChurchSchema


from services.church_service import (
  create_church,
  search_churchs_service, 
  update_church_service, 
  get_church_service, 
  delete_church_service,
  get_all_church_service,
  toggle_church_status_service
  )

from utils.decorators import staff_required, admin_required, role_required
from utils.inject_church_id import inject_church_id
from models.user_model import UserModel  

church_bp = Blueprint("church", __name__, url_prefix="/church")

"""
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1MzM1NjQ3OSwianRpIjoiYTBmMzA1ZTItZGE0YS00ZmZiLWJjMmItZjg3NTc3YjgzZDAyIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjY4MTI0ODU0ODI0MGU0NGVlZjE4MzE2NyIsIm5iZiI6MTc1MzM1NjQ3OSwiZXhwIjoxNzUzODk2NDc5LCJyb2xlIjoic3RhZmYifQ.jR4J3dwXfC08NvkbR0l2CQYhsgCV3bWk72gWadDI4_M
"""

# Créer un church uniqment par le staff
@church_bp.route("/create", methods=["POST"])
@jwt_required()
@staff_required
def create():
    """
    Créer un nouveau church avec sa licence et les informations de l’admin.
    ---
    tags:
      - Churchs
    consumes:
      - multipart/form-data
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        example: "Bearer votre.jwt.token"
      - in: formData
        name: denomination
        type: string
        required: true
        example: "Super Marché Wouri"
      - in: formData
        name: pays
        type: string
        required: true
        example: "Cameroun"
      - in: formData
        name: ville
        type: string
        required: true
        example: "Douala"
      - in: formData
        name: quartier
        type: string
        required: true
        example: "Akwa"
      - in: formData
        name: email
        type: string
        required: true
        example: "contact@wouri.com"
      - in: formData
        name: activité
        type: string
        required: true
        example: "Alimentation générale"
      - in: formData
        name: nombre_manager
        type: integer
        required: true
        example: 2
      - in: formData
        name: nombre_livreur
        type: integer
        required: true
        example: 10
      - in: formData
        name: admin
        type: string
        required: true
        description: Objet JSON contenant les informations de l'admin (name, first_name, email, password)
        example: '{"name": "Nguefack", "first_name": "Marius", "email": "marius.nguefack@exemple.com", "password": "Admin123"}'
      - in: formData
        name: image
        type: file
        required: false
        description: Logo ou image du church (format image)
    responses:
      200:
        description: church créé avec succès
      400:
        description: Données manquantes ou invalides
      401:
        description: Non autorisé (staff uniquement)
    """
    try:
        data = request.form.to_dict()
        logo_file = request.files.get("image")

        # Parser admin JSON
        if "admin" in data:
            try:
                data["admin"] = json.loads(data["admin"])
            except json.JSONDecodeError:
                return jsonify({"errors": {"admin": ["Format JSON invalide"]}}), 400


        # Valider les données
        errors = CreateChurchSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400

        # Appeler le service
        result = create_church(data, logo_file)
        return jsonify(result), result.get("status", 200)

    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500



# Mettre à jour les données d'un church (staff et admin)
@church_bp.route('/update/<string:church_id>', methods=['PUT'])
@jwt_required()
@role_required("staff")
def update_church(church_id):
    """
    Met à jour un church selon les permissions de l'utilisateur connecté.
    ---
    tags:
      - Churchs
    parameters:
      - name: church_id
        in: path
        required: true
        type: string
      - name: body
        in: body
        required: true
        schema:
          properties:
            denomination:
              type: string
            pays:
              type: string
            ville:
              type: string
            quartier:
              type: string
            email:
              type: string
            activité:
              type: string
            licence:
              type: object
              properties:
                max_managers:
                  type: integer
                max_livreurs:
                  type: integer
    security:
      - bearerAuth: []
    responses:
      200:
        description: church mis à jour
      403:
        description: Accès non autorisé
    """
    user_id = get_jwt_identity()
    user = UserModel.get_user_by_id(user_id)
    if not user:
        return jsonify({"message": "Utilisateur non trouvé"}), 404
    if user["role"] not in ["admin", "staff", "manager"]:  
        return jsonify({"message": "Accès non autorisé"}), 403
    # Récupérer les données de la requête
   
    update_data = request.get_json()
    errors = ChurchUpdateSchema().validate(update_data)
    if errors:
        return jsonify({"errors": errors}), 400

    return update_church_service(church_id, update_data, user["role"])
  
  
  
  
  #récupérer un church
@church_bp.route('/', methods=['GET'])

@role_required("admin", "staff", "manager", "livreur")
@jwt_required()
def get_info_church():
    """
    Récupérer un church par son ID.
    ---
    tags:
      - Churchs
    parameters:
      - name: church_id
        in: path
        required: true
        type: string
    responses:
      200:
        description: church trouvé
      404:
        description: church non trouvé
    """
    data = {}
    data = inject_church_id(data)
    church_id = data.get("church_id")
    if not church_id:
        return jsonify({"message": "ID de church manquant"}), 400
    church = get_church_service(church_id)
    
    if church:
        return jsonify(church), 200
    else:
        return jsonify({"message": "church non trouvé"}), 404
      
      
  #récupérer un church par son id
@church_bp.route('/<string:church_id>', methods=['GET'])
@role_required("admin", "staff", "manager", "livreur")
@jwt_required()
def get_info_church_details(church_id):
    """
    Récupérer un church par son ID.
    ---
    tags:
      - Churchs
    parameters:
      - name: church_id
        in: path
        required: true
        type: string
    responses:
      200:
        description: church trouvé
      404:
        description: church non trouvé
    """
    if not church_id:
        return jsonify({"message": "ID de church manquant"}), 400
    church = get_church_service(church_id)
    
    if church:
        return jsonify(church), 200
    else:
        return jsonify({"message": "church non trouvé"}), 404



# Supprimer un church
@church_bp.route('/delete/<string:church_id>', methods=['DELETE'])
@jwt_required()
@role_required("staff")
def delete_church(church_id):
    """
    Supprimer un church par son ID.
    ---
    tags:
      - Churchs
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        example: "Bearer votre.jwt.token"
    
      - name: church_id
        in: path
        required: true
        type: string
    responses:
      200:
        description: church supprimé avec succès
      404:
        description: church non trouvé
    """
    user_id = get_jwt_identity()
    user = UserModel.get_user_by_id(user_id)
    
    if not user or user["role"] != "staff":
        return jsonify({"message": "Accès non autorisé"}), 403
    
    result = delete_church_service(church_id)
    if not result:
        return jsonify({"message": "church non trouvé"}), 404
    
    if result["status"] == 200:
        return jsonify({"message": result["message"]}), 200
    else:
        return jsonify({"message": result["message"]}), result["status"]
      

# Récupérer tous les churchs
@church_bp.route('/all', methods=['GET'])
# @jwt_required()
# @role_required("staff")
def get_all_church():
    """
    Récupérer tous les churchs.
    ---
    tags:
      - Churchs
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        example: "Bearer votre.jwt.token"
    responses:
      200:
        description: Liste de tous les churchs
      500:
        description: Erreur serveur
    """
    try:
        churchs = get_all_church_service()
        return jsonify({"church": churchs}), 200
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération des churchs : {str(e)}"}), 500
      
@church_bp.route('/search', methods=['GET'])
def search_churchs():
    """
    Recherche de churchs avec filtres multiples
    ---
    tags:
      - Churchs
    summary: Recherche et filtre les churchs
    description: Permet de rechercher des churchs par dénomination, pays, ville et/ou quartier. Tous les paramètres sont optionnels et peuvent être combinés.
    
    parameters:
      - name: search
        in: query
        type: string
        required: false
        description: Recherche par dénomination du church (insensible à la casse)
        example: "Carrefour"
      - name: pays
        in: query
        type: string
        required: false
        description: Filtrer par pays
        example: "Cameroun"
      - name: ville
        in: query
        type: string
        required: false
        description: Filtrer par ville
        example: "Yaoundé"
      - name: quartier
        in: query
        type: string
        required: false
        description: Filtrer par quartier
        example: "Bastos"
    
    responses:
      200:
        description: Liste des churchs filtrés récupérée avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            count:
              type: integer
              description: Nombre de churchs trouvés
              example: 5
            filters:
              type: object
              description: Filtres appliqués
              properties:
                search:
                  type: string
                  example: "Super"
                pays:
                  type: string
                  example: "Cameroun"
                ville:
                  type: string
                  example: "Douala"
                quartier:
                  type: string
                  example: "Akwa"
            data:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "60d5ec49f1b2c8a9e4f3b1a2"
                  denomination:
                    type: string
                    example: "Super Marché Central"
                  pays:
                    type: string
                    example: "Cameroun"
                  ville:
                    type: string
                    example: "Yaoundé"
                  quartier:
                    type: string
                    example: "Centre-ville"
                  email:
                    type: string
                    example: "contact@supermarche.cm"
                  activité:
                    type: string
                    example: "Commerce de détail"
                  logo:
                    type: string
                    example: "http://localhost:5000/uploads/images/logo_magasin.png"
                  licence:
                    type: object
                    properties:
                      max_managers:
                        type: integer
                        example: 5
                      max_livreurs:
                        type: integer
                        example: 10
                  is_active:
                    type: boolean
                    example: true
                  created_at:
                    type: string
                    format: date-time
                  utilisateurs:
                    type: array
                    items:
                      type: object
                      properties:
                        _id:
                          type: string
                        name:
                          type: string
                        email:
                          type: string
                        role:
                          type: string
      500:
        description: Erreur serveur lors de la recherche
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Erreur lors de la récupération des churchs : ..."
    """
    search_query = request.args.get('search', None)
    pays = request.args.get('pays', None)
    ville = request.args.get('ville', None)
    quartier = request.args.get('quartier', None)
    
    try:
        churchs = search_churchs_service(
            search_query=search_query,
            pays=pays,
            ville=ville,
            quartier=quartier
        )
        
        return jsonify({
            "success": True,
            "count": len(churchs),
            "filters": {
                "search": search_query,
                "pays": pays,
                "ville": ville,
                "quartier": quartier
            },
            "data": churchs
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur lors de la récupération des churchs : {str(e)}"
        }), 500

@church_bp.route("<string:church_id>/toggle-status", methods=["PUT"])
@jwt_required()
@staff_required
def toggle_church_status_route(church_id):
    """
    Route pour activer ou désactiver un church.
    """
    result = toggle_church_status_service(church_id)
    return jsonify(result), result["status"]