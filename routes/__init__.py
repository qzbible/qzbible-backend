from .church_routes import church_bp 


def register_routes(app):
    app.register_blueprint(church_bp)
