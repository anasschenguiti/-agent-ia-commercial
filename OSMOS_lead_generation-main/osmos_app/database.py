import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def init_db(app):
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///osmos.db')
    
    # Ensures absolute path for sqlite db inside osmos_app folder if it's a relative sqlite path
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
        db_path = db_url.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            base_dir = os.path.abspath(os.path.dirname(__file__))
            db_url = f"sqlite:///{os.path.join(base_dir, db_path)}"

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        import models  # Register the models
        db.create_all()
