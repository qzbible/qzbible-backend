from .magasin import magasin_bp 


def register_routes(app):
    app.register_blueprint(magasin_bp)
