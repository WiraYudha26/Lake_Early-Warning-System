from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
        
    app.config['EMAIL_USER'] = os.getenv("EMAIL_USER")
    app.secret_key = os.getenv("SECRET_KEY", "default-secret-key")
    
    from .routes import main
    app.register_blueprint(main)
    
    return app
