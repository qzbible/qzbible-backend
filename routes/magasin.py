from flask import Blueprint, request, jsonify
import json
from flask_jwt_extended import jwt_required, get_jwt_identity
from schemas.magasin_schema import CreateMagasinSchema, MagasinUpdateSchema
from services.magasin_service import (
  create_magasin,
  search_magasins_service, 
  update_magasin_service, 
  get_magasin_service, 
  delete_magasin_service,
  get_all_magasin_service,
  toggle_magasin_status_service
  )

from utils.decorators import staff_required, admin_required, role_required
from utils.inject_magasin_id import inject_magasin_id
from models.user_model import UserModel  

magasin_bp = Blueprint("magasin", __name__, url_prefix="/magasin")

"""
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1MzM1NjQ3OSwianRpIjoiYTBmMzA1ZTItZGE0YS00ZmZiLWJjMmItZjg3NTc3YjgzZDAyIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjY4MTI0ODU0ODI0MGU0NGVlZjE4MzE2NyIsIm5iZiI6MTc1MzM1NjQ3OSwiZXhwIjoxNzUzODk2NDc5LCJyb2xlIjoic3RhZmYifQ.jR4J3dwXfC08NvkbR0l2CQYhsgCV3bWk72gWadDI4_M
"""

# Créer un magasin uniqment par le staff
@magasin_bp.route("/create", methods=["POST"])
@jwt_required()
@staff_required
def create():
    """
    Créer un nouveau magasin avec sa licence et les informations de l’admin.
    ---
    tags:
      - Magasins
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
        description: Logo ou image du magasin (format image)
    responses:
      200:
        description: Magasin créé avec succès
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
        errors = CreateMagasinSchema().validate(data)
        if errors:
            return jsonify({"errors": errors}), 400

        # Appeler le service
        result = create_magasin(data, logo_file)
        return jsonify(result), result.get("status", 200)

    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500



# Mettre à jour les données d'un magasin (staff et admin)
@magasin_bp.route('/update/<string:magasin_id>', methods=['PUT'])
@jwt_required()
@role_required("staff")
def update_magasin(magasin_id):
    """
    Met à jour un magasin selon les permissions de l'utilisateur connecté.
    ---
    tags:
      - Magasins
    parameters:
      - name: magasin_id
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
        description: Magasin mis à jour
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
    errors = MagasinUpdateSchema().validate(update_data)
    if errors:
        return jsonify({"errors": errors}), 400

    return update_magasin_service(magasin_id, update_data, user["role"])
  
  
  
  
  #récupérer un magasin
@magasin_bp.route('/', methods=['GET'])

@role_required("admin", "staff", "manager", "livreur")
@jwt_required()
def get_info_magasin():
    """
    Récupérer un magasin par son ID.
    ---
    tags:
      - Magasins
    parameters:
      - name: magasin_id
        in: path
        required: true
        type: string
    responses:
      200:
        description: Magasin trouvé
      404:
        description: Magasin non trouvé
    """
    data = {}
    data = inject_magasin_id(data)
    magasin_id = data.get("magasin_id")
    if not magasin_id:
        return jsonify({"message": "ID de magasin manquant"}), 400
    magasin = get_magasin_service(magasin_id)
    
    if magasin:
        return jsonify(magasin), 200
    else:
        return jsonify({"message": "Magasin non trouvé"}), 404
      
      
  #récupérer un magasin par son id
@magasin_bp.route('/<string:magasin_id>', methods=['GET'])
@role_required("admin", "staff", "manager", "livreur")
@jwt_required()
def get_info_magasin_details(magasin_id):
    """
    Récupérer un magasin par son ID.
    ---
    tags:
      - Magasins
    parameters:
      - name: magasin_id
        in: path
        required: true
        type: string
    responses:
      200:
        description: Magasin trouvé
      404:
        description: Magasin non trouvé
    """
    if not magasin_id:
        return jsonify({"message": "ID de magasin manquant"}), 400
    magasin = get_magasin_service(magasin_id)
    
    if magasin:
        return jsonify(magasin), 200
    else:
        return jsonify({"message": "Magasin non trouvé"}), 404



# Supprimer un magasin
@magasin_bp.route('/delete/<string:magasin_id>', methods=['DELETE'])
@jwt_required()
@role_required("staff")
def delete_magasin(magasin_id):
    """
    Supprimer un magasin par son ID.
    ---
    tags:
      - Magasins
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        example: "Bearer votre.jwt.token"
    
      - name: magasin_id
        in: path
        required: true
        type: string
    responses:
      200:
        description: Magasin supprimé avec succès
      404:
        description: Magasin non trouvé
    """
    user_id = get_jwt_identity()
    user = UserModel.get_user_by_id(user_id)
    
    if not user or user["role"] != "staff":
        return jsonify({"message": "Accès non autorisé"}), 403
    
    result = delete_magasin_service(magasin_id)
    if not result:
        return jsonify({"message": "Magasin non trouvé"}), 404
    
    if result["status"] == 200:
        return jsonify({"message": result["message"]}), 200
    else:
        return jsonify({"message": result["message"]}), result["status"]
      

# Récupérer tous les magasins
@magasin_bp.route('/all', methods=['GET'])
# @jwt_required()
# @role_required("staff")
def get_all_magasin():
    """
    Récupérer tous les magasins.
    ---
    tags:
      - Magasins
    parameters:
      - in: header
        name: Authorization
        required: true
        schema:
          type: string
        example: "Bearer votre.jwt.token"
    responses:
      200:
        description: Liste de tous les magasins
      500:
        description: Erreur serveur
    """
    try:
        magasins = get_all_magasin_service()
        return jsonify({"church": magasins}), 200
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération des magasins : {str(e)}"}), 500
      
@magasin_bp.route('/search', methods=['GET'])
def search_magasins():
    """
    Recherche de magasins avec filtres multiples
    ---
    tags:
      - Magasins
    summary: Recherche et filtre les magasins
    description: Permet de rechercher des magasins par dénomination, pays, ville et/ou quartier. Tous les paramètres sont optionnels et peuvent être combinés.
    
    parameters:
      - name: search
        in: query
        type: string
        required: false
        description: Recherche par dénomination du magasin (insensible à la casse)
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
        description: Liste des magasins filtrés récupérée avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            count:
              type: integer
              description: Nombre de magasins trouvés
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
              example: "Erreur lors de la récupération des magasins : ..."
    """
    search_query = request.args.get('search', None)
    pays = request.args.get('pays', None)
    ville = request.args.get('ville', None)
    quartier = request.args.get('quartier', None)
    
    try:
        magasins = search_magasins_service(
            search_query=search_query,
            pays=pays,
            ville=ville,
            quartier=quartier
        )
        
        return jsonify({
            "success": True,
            "count": len(magasins),
            "filters": {
                "search": search_query,
                "pays": pays,
                "ville": ville,
                "quartier": quartier
            },
            "data": magasins
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erreur lors de la récupération des magasins : {str(e)}"
        }), 500

@magasin_bp.route("<string:magasin_id>/toggle-status", methods=["PUT"])
@jwt_required()
@staff_required
def toggle_magasin_status_route(magasin_id):
    """
    Route pour activer ou désactiver un magasin.
    """
    result = toggle_magasin_status_service(magasin_id)
    return jsonify(result), result["status"]