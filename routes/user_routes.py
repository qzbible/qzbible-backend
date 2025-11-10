import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from utils.decorators import admin_required, staff_required
from utils.inject_church_id import inject_church_id
from utils.inject_magasin_id import inject_magasin_id, inject_magasin_id_with_email
from utils.decorators import role_required
from models.user_model import UserModel
from services.user_service import (   
    create_simple_user,
    create_staff_account,
    create_admin_account,
    activate_user_by_email, 
  create_manager,
 
    delete_user_service,
    get_user_by_id_service,
    get_all_users_service,
    update_user_service,
    activate_user_by_id,
    deactivate_user_by_id,
    set_user_activation,
    reset_password_service
)
from bson.objectid import ObjectId
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
from werkzeug.utils import secure_filename


user_bp = Blueprint('user_routes', __name__, url_prefix='/users')
@user_bp.route('/create_staff', methods=['POST'])
def create_staff():
    """
    Créer un compte staff
    ---
    tags:
      - Authentification
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - first_name
            - email
            - password
            - confirm_password
          properties:
            name:
              type: string
              example: "Nguefack"
            first_name:
              type: string
              example: "Marius"
            email:
              type: string
              example: "marius@gmail.com"
            password:
              type: string
              example: "pass123"
            confirm_password:
              type: string
              example: "pass123"
    responses:
      200:
        description: Compte staff créé
      400:
        description: Données invalides
    """
    data = request.get_json()
    name = data.get('name')
    first_name = data.get('first_name')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    if not email or not password:
        return jsonify({"error": "Email et mot de passe sont requis."}), 400
    
    return create_staff_account(name, first_name, email, password, confirm_password)


# Créer un admin

@user_bp.route('/create_admin', methods=['POST'])
@jwt_required()
@staff_required
def create_admin():
    """
    Créer un compte admin pour un magasin
    ---
    tags:
      - Authentification
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - first_name
            - email
            - magasin_id
          properties:
            name:
              type: string
              example: "Kamtchou"
            first_name:
              type: string
              example: "Yannick"
            email:
              type: string
              example: "yannick@admin.com"
            magasin_id:
              type: string
              example: "magasin123"
    responses:
      200:
        description: Compte admin créé
      400:
        description: Données manquantes
    """
    data = request.get_json()
    data = inject_magasin_id(data)
    name = data.get('name')
    first_name = data.get('first_name')
    email = data.get('email')
    magasin_id = data.get('magasin_id')
    password = data.get('password', None)
    
    if not email or not magasin_id:
        return jsonify({"error": "Email et magasin_id sont requis."}), 400
    if not password:
        return jsonify({"error": "Le mot de passe est requis."}), 400
    return create_admin_account(name, first_name, email, password,  magasin_id)


# Le staff peut activer un compte un utilisateur via son email
@user_bp.route('/activate-user/<string:email>', methods=['POST'])
@staff_required
@jwt_required()
def activate_user(email):
    """
    Activer un compte utilisateur via son email.
    ---
    tags:
      - Utilisateurs
    parameters:
      - name: email
        in: path
        type: string
        required: true
        description: Email de l'utilisateur à activer
      - in: body
        name: body
        required: true
        description: Mot de passe à définir pour activer le compte
        schema:
          type: object
          required:
            - password
          properties:
            password:
              type: string
              example: motDePasse123
    responses:
      200:
        description: Compte activé avec succès
      400:
        description: Le mot de passe est requis
      404:
        description: Utilisateur introuvable
    """
    data = request.get_json()
    password = data.get('password')
    
    if not password:
        return jsonify({"error": "Le mot de passe est requis"}), 400
    result = activate_user_by_email(email, password)    
    return jsonify(result), result.get("status", 200)


# Le staff peut activer un compte un utilisateur via son id
@user_bp.route('/activate-user/<string:id>', methods=['PUT'])
@role_required("admin", "staff", "manager")
@jwt_required()
def activate_user_with_id(id):
    """
    Activer un compte utilisateur via son email.
    ---
    tags:
      - Utilisateurs
    parameters:
      - name: id
        in: path
        type: string
        required: true
        description: id de l'utilisateur à activer
      - in: body
        name: body
        required: true
        description: Mot de passe à définir pour activer le compte
        schema:
          type: object
          required:
            - password
          properties:
            password:
              type: string
              example: motDePasse123
    responses:
      200:
        description: Compte activé avec succès
      400:
        description: Le mot de passe est requis
      404:
        description: Utilisateur introuvable
    """
    print(f"ID de l'utilisateur à activer : {id}")
    result = set_user_activation(id, activate=True) 
       
    return jsonify(result), result.get("status", 200)


# Le staff peut desactiver un compte un utilisateur via son id
@user_bp.route('/deactivate-user/<string:id>', methods=['PUT'])
@role_required("admin", "staff", "manager")
@jwt_required()
def deactivate_user_with_id(id):
    """
    Activer un compte utilisateur via son email.
    ---
    tags:
      - Utilisateurs
    parameters:
      - name: id
        in: path
        type: string
        required: true
        description: id de l'utilisateur à activer
      - in: body
        name: body
        required: true
        description: Mot de passe à définir pour activer le compte
        schema:
          type: object
          required:
            - password
          properties:
            password:
              type: string
              example: motDePasse123
    responses:
      200:
        description: Compte activé avec succès
      400:
        description: Le mot de passe est requis
      404:
        description: Utilisateur introuvable
    """
    print(f"ID de l'utilisateur à activer : {id}")
    result = set_user_activation(id, activate=False) 
       
    return jsonify(result), result.get("status", 200)

 
# Créer un manager
@user_bp.route('/create_manager', methods=['POST'])
@jwt_required()
@admin_required
def create_manager_route():
    """
    Créer un nouveau manager pour un magasin.
    ---
    tags:
      - Utilisateurs
    parameters:
      - in: body
        name: body
        required: true
        description: Informations du manager
        schema:
          type: object
          required:
            - name
            - first_name
            - email
            - church_id
          properties:
            name:
              type: string
              example: "Smith"
            first_name:
              type: string
              example: "Anna"
            email:
              type: string
              example: "anna.smith@email.com"
            church_id:
              type: string
              example: "66325fd5379a7338c9cd51a2"
    responses:
      200:
        description: Manager créé avec succès
      400:
        description: Tous les champs sont requis
    """
    data = request.get_json()
    data = inject_church_id(data)
    name = data.get('name')
    first_name = data.get('first_name')
    email = data.get('email')
    church_id = data.get('church_id')
    password = data.get('password')
    if not password:
        return jsonify({"error": "Le mot de passe est requis"}), 400
    
    if not name or not first_name or not email or not church_id:
        return jsonify({"error": "Tous les champs sont requis"}), 400
    
    result = create_manager(name, first_name, email, password,  church_id)
    if isinstance(result, tuple):
          data, status = result
    else:
        data, status = result, 200
    
    return jsonify(data), status

# Route pour obtenir les informations sur un utilisateur
@user_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Obtenir les informations de l'utilisateur connecté.
    ---
    tags:
      - Utilisateurs
    security:
      - bearerAuth: []
    responses:
      200:
        description: Informations de l'utilisateur récupérées avec succès
        schema:
          type: object
          properties:
            _id:
              type: string
              example: "661f518c1f48b44f4df8a394"
            name:
              type: string
              example: "Doe"
            first_name:
              type: string
              example: "John"
            email:
              type: string
              example: "john.doe@email.com"
            role:
              type: string
              example: "admin"
            avatar:
              type: string
              example: "/uploads/avatars/661f518c1f48b44f4df8a394_avatar.png"
      401:
        description: Token JWT manquant ou invalide
      404:
        description: Utilisateur non trouvé
    """
    user_id = get_jwt_identity()
    user = UserModel.get_user_by_id(user_id)

    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    user['_id'] = str(user['_id'])
    return jsonify(user), 200

#Créer un livreur  
@user_bp.route('/create_user', methods=['POST'])
def create_simple_user_route():
    """
    Créer un nouveau livreur pour un magasin.
    ---
    tags:
      - Utilisateurs
    parameters:
      - in: body
        name: body
        required: true
        description: Informations du livreur
        schema:
          type: object
          required:
            - name
            - age_group
            - email
            - church_id
          properties:
            name:
              type: string
              example: "Doe"
            age_group:
              type: string
              example: "10-18 ans"
            email:
              type: string
              example: "john.doe@email.com"
            church_id:
              type: string
              example: "66325fd5379a7338c9cd51a1"
    responses:
      200:
        description: Livreur créé avec succès
      400:
        description: Tous les champs sont requis
    """
    data = request.get_json()
    name = data.get('name')
    age_group = data.get('age_group')
    email = data.get('email')
    church_id = data.get('church_id')
    password = "66325fd5379a7338c9cd51a1"
    
    if not name or not age_group or not email or not church_id:
        return jsonify({"error": "Tous les champs sont requis"}), 400
    if not password:
        return jsonify({"error": "Le mot de passe est requis"}), 400
    result = create_simple_user(name, age_group, email, password,  church_id)
    if isinstance(result, tuple):
          data, status = result
    else:
        data, status = result, 200
    
    return jsonify(data), status


UPLOAD_FOLDER = 'uploads/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Créer le dossier s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route permettant d'uploader un avatar
@user_bp.route('/upload_avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    """
    Upload d’un avatar pour l'utilisateur connecté.
    ---
    tags:
      - Utilisateurs
    consumes:
      - multipart/form-data
    security:
      - bearerAuth: []
    parameters:
      - name: avatar
        in: formData
        type: file
        required: true
        description: Image de l'avatar (jpg, png, gif, jpeg)
    responses:
      200:
        description: Avatar mis à jour avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: Avatar mis à jour
            avatar_url:
              type: string
              example: /uploads/avatars/661f518c1f48b44f4df8a394_avatar.png
      400:
        description: Requête invalide ou fichier non autorisé
      401:
        description: Token JWT manquant ou invalide
    """
    current_user_id = get_jwt_identity()
    if 'avatar' not in request.files:
        return jsonify({"error": "Aucun fichier envoyé"}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({"error": "Nom de fichier vide"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, f"{current_user_id}_{filename}")
        file.save(path)

        # Mise à jour du user en base
        avatar_url = f"/{path}"  # Si serveur local. Pour un CDN, stocker l'URL
        UserModel.update_avatar(user_id=current_user_id, avatar_url=avatar_url)

        return jsonify({"message": "Avatar mis à jour", "avatar_url": avatar_url}), 200
    
    return jsonify({"error": "Format de fichier non autorisé"}), 400
 
    
# Récupérer un utilisateur par son ID
@user_bp.route('/<string:user_id>', methods=['GET'])
@jwt_required()
@role_required("admin", "staff", "manager", "livreur")
def get_user_by_id(user_id):
    """
    Récupérer les informations d'un utilisateur par son ID.
    ---
    tags:
      - Utilisateurs
    parameters:
      - name: user_id
        in: path
        type: string
        required: true
        description: ID de l'utilisateur à récupérer
    responses:
      200:
        description: Informations de l'utilisateur récupérées avec succès
      404:
        description: Utilisateur non trouvé
    """
    return get_user_by_id_service(user_id)
  
# Supprimer un utilisateur par son ID
@user_bp.route('/<string:user_id>', methods=['DELETE'])
@jwt_required()
@role_required("admin", "staff", "manager")
def delete_user(user_id):
    """
    Supprimer un utilisateur par son ID.
    ---
    tags:
      - Utilisateurs
    parameters:
      - name: user_id
        in: path
        type: string
        required: true
        description: ID de l'utilisateur à supprimer
    responses:
      200:
        description: Utilisateur supprimé avec succès
      404:
        description: Utilisateur non trouvé
    """
    print(f"Suppression de l'utilisateur avec ID : {user_id}")
    return delete_user_service(user_id)
  
  
# Mettre à jour un utilisateur
@user_bp.route('/<string:user_id>', methods=['PUT'])
@jwt_required()
@role_required("admin", "staff", "manager")
def update_user(user_id):
  return update_user_service(user_id, data=request.get_json())


# Récupérer tous les utilisateurs
@user_bp.route('/', methods=['GET'])
@jwt_required()
@role_required("admin", "staff", "manager")
def get_all_users():
    """
    Récupérer tous les utilisateurs.
    ---
    tags:
      - Utilisateurs
    responses:
      200:
        description: Liste de tous les utilisateurs récupérée avec succès
      500:
        description: Erreur lors de la récupération des utilisateurs
    """
    return get_all_users_service()
  

# Réinitialiser le mot de passe d'un utilisateur
@user_bp.route('/reset-password/<user_id>', methods=['POST'])
@jwt_required()
@role_required("admin", "staff", "manager")
def reset_password(user_id):
    """
    Réinitialiser le mot de passe d'un utilisateur.
    ---
    tags:
      - Utilisateurs
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - user_id
            - new_password
          properties:
            user_id:
              type: string
              example: "661f518c1f48b44f4df8a394"
            new_password:
              type: string
              example: "nouveauMotDePasse123"
    responses:
      200:
        description: Mot de passe réinitialisé avec succès
      400:
        description: Données invalides ou mot de passe trop court
      404:
        description: Utilisateur non trouvé
    """
    data = request.get_json()
    return reset_password_service(user_id, data)



UPLOAD_FOLDER = '/mnt/user-data/uploads/videos'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@user_bp.route("/video", methods=["POST"])
@jwt_required()
def upload_video():
    """
    Upload une vidéo et retourne le lien
    ---
    tags:
      - Uploads
    consumes:
      - multipart/form-data
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: Token JWT de l'utilisateur
        example: "Bearer votre.jwt.token"
      - in: formData
        name: video
        type: file
        required: true
        description: Fichier vidéo à uploader (mp4, avi, mov, mkv, webm - max 100MB)
    responses:
      200:
        description: Vidéo uploadée avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Vidéo uploadée avec succès"
            video_url:
              type: string
              example: "https://votre-domaine.com/uploads/videos/abc123.mp4"
            filename:
              type: string
              example: "abc123.mp4"
      400:
        description: Aucun fichier fourni ou format non autorisé
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Format de fichier non autorisé"
      401:
        description: Token JWT manquant ou invalide
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Erreur : ..."
    """
    try:
        if 'video' not in request.files:
            return jsonify({"message": "Aucun fichier fourni"}), 400
        
        file = request.files['video']
        
        if file.filename == '':
            return jsonify({"message": "Nom de fichier vide"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"message": "Format de fichier non autorisé"}), 400
        
        # Générer un nom unique
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        
        # Créer le dossier si nécessaire
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Sauvegarder le fichier
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Retourner le lien
        video_url = f"https://dev-backend.qzbible.com/uploads/videos/{filename}"
        
        return jsonify({
            "message": "Vidéo uploadée avec succès",
            "video_url": video_url,
            "filename": filename
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur : {str(e)}"}), 500

