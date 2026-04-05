from flask import Flask
from .config import Config
from .database import init_db
from .routes import register_routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializace databáze
    with app.app_context():
        init_db()

    # Registrace rout
    register_routes(app)

    return app
