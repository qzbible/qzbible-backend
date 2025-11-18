# app.py
import os
from flask import Flask, jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from config import Config
from flask_cors import CORS
from extensions import mongo, jwt, mail
from models.otp_model import OTPModel
from werkzeug.exceptions import HTTPException
from bson.errors import InvalidId
from flasgger import Swagger


# Initialisation des extensions
blacklist = set()

def create_app():
    """Factory pour créer et configurer l'application Flask."""
    
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)
    app.config['DEBUG'] = True
    # Créer automatiquement le dossier d'upload si nécessaire
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    # Créer automatiquement le dossier pour les images de staff si nécessaire
    os.makedirs(app.config["STAFF_IMAGE_FOLDER"], exist_ok=True)


    # Initialisation des extensions avec l'app Flask
    mongo.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)


    Config.init_app(app)
    
    # Enregistrement des Blueprints
    from routes.church_routes import church_bp
    from routes.auth import auth_bp
    from routes.user_routes import user_bp
    from routes.staff_routes import staff_bp
    from routes.sections_routes import sections_bp
    from routes.dashboard_routes import dashboard_bp

    from routes.chapters_routes import chapters_bp
    from routes.quizzes_routes import quizzes_bp
    from routes.quiz_attempts import quiz_attempts_bp
    from routes.catalog_routes import catalog_bp
    from routes.manual_unlocks_routes import manual_unlocks_bp
    from routes.user_progress_routes import user_progress_bp

    from routes.reading_plan_routes import reading_plan_bp
    from routes.documents_routes import documents_bp
   

    from routes.otp_routes import otp_bp
    
    app.register_blueprint(user_bp)
 
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(otp_bp)
    app.register_blueprint(church_bp)
    app.register_blueprint(sections_bp)
    app.register_blueprint(chapters_bp)
    app.register_blueprint(quizzes_bp)
    app.register_blueprint(quiz_attempts_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(manual_unlocks_bp)
    app.register_blueprint(user_progress_bp)

    app.register_blueprint(documents_bp)
    app.register_blueprint(reading_plan_bp)
    
    # CORS : autoriser le front React à communiquer avec le backend
    CORS(app, supports_credentials=True, origins=[Config.ALLOWED_ORIGINS])
    
    # Gestion du token blacklisté
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return jti in blacklist

    # Gestion des erreurs globales
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return jsonify({"681a2386c5a2a10fd9d93874": str(error)}), error.code

    # Gestion des erreurs MongoDB InvalidId
    @app.errorhandler(InvalidId)
    def handle_invalid_id(error):
        return jsonify({"error": "ID non valide."}), 400

    
    # Route pour la documentation de l'API
    @app.route('/')
    def docs():
        return jsonify({
            "message": "Documentation de l'API",
            "url": "/apidocs/"
        }), 200
    
    @app.route('/test-db')
    def test_db():
        try:
            # Ping MongoDB
            mongo.db.command('ping')
            
            # Lister les collections
            collections = mongo.db.list_collection_names()
            
            return jsonify({
                "status": "✅ Connexion MongoDB OK",
                "database": mongo.db.name,
                "collections": collections
            }), 200
        except Exception as e:
            return jsonify({
                "status": "❌ Erreur de connexion",
                "error": str(e)
            }), 500
    
     
    swagger = Swagger(app, template={
        "swagger": "2.0",
        "info": {
            "title": "Quiz Bible API",
            "description": "API de croissance spirituelle ",
            "version": "1.0.0"
        },
        "host": os.getenv("BASE_URL", "localhost:5000"),  # Votre domaine
        "basePath": "/",
        "schemes": ["https", "http"],  # HTTPS EN PREMIER !
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: **'Authorization: Bearer &lt;token&gt;'**"
            }
        },
        "security": [
            {
                "Bearer": []
            }
        ]
    })

    
    from flask import send_from_directory, current_app
    # Route pour servir les fichiers uploadés
    @app.route("/uploads/images/<filename>")
    def uploaded_file(filename):
        return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
    
    #Route pour servir les images de staff
    @app.route("/uploads/staff_images/<filename>")
    def staff_uploaded_file(filename):
        return send_from_directory(current_app.config["STAFF_IMAGE_FOLDER"], filename)

    # ========== COMMANDES CLI ==========
    import click
    
    @app.cli.command('init-images')
    @click.option('--folder', default=None, help='Chemin du dossier source (optionnel)')
    @click.option('--categorie', default='general', help='Catégorie par défaut des images')
    def init_images_command(folder, categorie):
        """
        Initialise les images depuis un dossier local
        
        Usage:
            flask init-images                                    # Utilise le dossier par défaut
            flask init-images --categorie=branding              # Dossier par défaut avec catégorie
            flask init-images --folder=/chemin/vers/dossier     # Dossier personnalisé
        """
        from scripts.init_images import init_images_from_local
        
        # Si aucun dossier n'est spécifié, utiliser le dossier par défaut
        if folder is None:
            folder = app.config.get('DEFAULT_IMAGES_FOLDER')
            click.echo(click.style(
                f"📁 Utilisation du dossier par défaut: {folder}\n",
                fg='cyan'
            ))
        
        with app.app_context():
            result = init_images_from_local(
                source_folder=folder,
                categorie_default=categorie,
                app_config=app.config
            )
            
            if result.get("success"):
                click.echo(click.style(
                    f"\n✅ {result['imported']} image(s) importée(s) avec succès!",
                    fg='green', bold=True
                ))
                click.echo(f"❌ Erreurs: {result['errors']}")
                click.echo(f"⏭️  Ignorés: {result['skipped']}")
            else:
                click.echo(click.style(
                    f"\n❌ Erreur: {result.get('message')}",
                    fg='red', bold=True
                ))
    
    #  Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MTg2NTcwMiwianRpIjoiNjhmZTY4M2EtMGJmMi00ZjY4LTk1ZjgtZDgzYzQwZWMyYzM0IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjY4ZmViMGNmNGE2NDc1ZWUyMTJiZWVmYiIsIm5iZiI6MTc2MTg2NTcwMiwiZXhwIjoyMDc3MjI1NzAyLCJyb2xlIjoiYWRtaW4ifQ.6ojkFzPdUtXYfH_K_yEuQipTykzdjmeNyut4PvO7d7w
    @app.cli.command('list-images')
    @click.option('--categorie', default=None, help='Filtrer par catégorie')
    def list_images_command(categorie):
        """Liste toutes les images dans la base de données"""
        from models.image_staff_model import ImageStaffModel
        
        with app.app_context():
            if categorie:
                images = ImageStaffModel.get_image_by_critere(categorie=categorie)
                click.echo(click.style(
                    f"\n📊 Images de la catégorie '{categorie}':\n",
                    fg='cyan', bold=True
                ))
            else:
                images = ImageStaffModel.get_all_images()
                click.echo(click.style(
                    f"\n📊 Toutes les images:\n",
                    fg='cyan', bold=True
                ))
            
            if not images:
                click.echo(click.style("⚠️  Aucune image trouvée", fg='yellow'))
                return
            
            click.echo(f"Total: {len(images)} image(s)\n")
            
            for img in images:
                click.echo(f"  📷 {img.get('nom', 'Sans nom')}")
                click.echo(f"     ID: {img['_id']}")
                click.echo(f"     Fichier: {img.get('filename', 'N/A')}")
                click.echo(f"     Catégorie: {img.get('categorie', 'N/A')}")
                click.echo(f"     Tags: {', '.join(img.get('tags', []))}")
                click.echo()
    
    
    @app.cli.command('clear-images')
    @click.confirmation_option(
        prompt='⚠️  Êtes-vous sûr de vouloir supprimer TOUTES les images ?'
    )
    def clear_images_command():
        """Supprime toutes les images de la base de données et du serveur"""
        from models.image_staff_model import ImageStaffModel
        import shutil
        
        with app.app_context():
            # Supprimer de la base de données
            result = ImageStaffModel.collection.delete_many({})
            click.echo(click.style(
                f"✓ {result.deleted_count} image(s) supprimée(s) de la base de données",
                fg='green'
            ))
            
            # Nettoyer le dossier
            staff_folder = app.config.get('STAFF_IMAGE_FOLDER')
            if os.path.exists(staff_folder):
                shutil.rmtree(staff_folder)
                os.makedirs(staff_folder, exist_ok=True)
                click.echo(click.style(
                    f"✓ Dossier {staff_folder} nettoyé",
                    fg='green'
                ))
    
    
    
    from flask import send_from_directory
    import os

    @app.route('/files/documents/<filename>')
    def serve_pdf_file(filename):
        """
        Servir les fichiers PDF directement via URL
        """
        try:
            documents_dir = os.path.join(app.config.get('UPLOAD_FOLDER', '/tmp'), 'documents')
            return send_from_directory(documents_dir, filename, mimetype='application/pdf')
        except Exception as e:
            return "Fichier non trouvé", 404
        
    return app





# Point d'entrée
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
