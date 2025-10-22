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
    # Créer automatiquement le dossier d'upload si nécessaire
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    # Créer automatiquement le dossier pour les images de staff si nécessaire
    os.makedirs(app.config["STAFF_IMAGE_FOLDER"], exist_ok=True)


    # Initialisation des extensions avec l'app Flask
    mongo.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)

    with app.app_context():
        OTPModel.initialize_indexes()
    Config.init_app(app)
    
    # Enregistrement des Blueprints
    from routes.magasin import magasin_bp
    from routes.auth import auth_bp
    from routes.user_routes import user_bp
    from routes.staff_routes import staff_bp
    from routes.categorie_routes import categorie_bp
    from routes.produit_routes import produit_bp
    from routes.client_route import client_bp
    from routes.commande_routes import commande_bp
    from routes.approvisionnement_routes import approvisionnement_bp
    from routes.livraison_routes import livraison_bp
    from routes.dashboard_routes import dashboard_bp
    from routes.notification_routes import notification_bp

    from routes.otp_routes import otp_bp
    
    app.register_blueprint(user_bp)
    app.register_blueprint(magasin_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(categorie_bp)   
    app.register_blueprint(produit_bp)
    app.register_blueprint(client_bp)
    #app.register_blueprint(commande_bp)
    app.register_blueprint(approvisionnement_bp)
    app.register_blueprint(livraison_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(notification_bp)

    app.register_blueprint(otp_bp)
    
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
    
     
    swagger = Swagger(app, template={
        "swagger": "2.0",
        "info": {
            "title": "QZBible API",
            "description": "API de gestion de livraison avec rôles, JWT, création de magasin, etc.",
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
    return app





# Point d'entrée
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
