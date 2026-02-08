from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # Registrar Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.tools import tools_bp
    from app.routes.profile import profile_bp # Nueva línea

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(tools_bp, url_prefix='/tools')
    app.register_blueprint(profile_bp) # Nueva línea

    @app.context_processor
    def inject_theme():
        # Evitamos importar SiteConfig arriba para evitar ciclos, o usamos imports dentro
        from app.models import SiteConfig
        theme_conf = SiteConfig.query.filter_by(key='current_theme').first()
        theme = theme_conf.value if theme_conf else 'theme-dark'
        return dict(current_theme=theme)

    # Crear tablas de base de datos si no existen
    with app.app_context():
        db.create_all()
        # Crear usuario admin por defecto si no existe
        from app.models import User
        from werkzeug.security import generate_password_hash
        
        admin_user = User.query.filter_by(username='ADMIN').first()
        if not admin_user:
            hashed_pw = generate_password_hash('1188964') # Contraseña del código original
            new_admin = User(username='ADMIN', password_hash=hashed_pw, role='admin', status='active')
            db.session.add(new_admin)
            db.session.commit()
            print("Usuario ADMIN creado por defecto.")

    return app
