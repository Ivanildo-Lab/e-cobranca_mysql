# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap5
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_login import LoginManager # Importa LoginManager
from config import Config
import datetime
from datetime import date

# --- Instancia as extensões FORA de create_app ---
db = SQLAlchemy()
migrate = Migrate()
bootstrap = Bootstrap5()
csrf = CSRFProtect()
login_manager = LoginManager()

# Configurações do Flask-Login (fora de create_app)
login_manager.login_view = 'auth.login' # Nome do blueprint 'auth', função 'login'
login_manager.login_message = 'Por favor, faça o login para acessar esta página.'
login_manager.login_message_category = 'info'
# -------------------------------------------------

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Validação da SECRET_KEY (essencial para CSRF e Sessões)
    if not app.config['SECRET_KEY']:
        raise ValueError("Necessário definir a SECRET_KEY na configuração.")

    # --- Inicializa as extensões com o app DENTRO de create_app ---
    db.init_app(app)
    migrate.init_app(app, db)
    bootstrap.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app) # Inicializa Flask-Login
    # -------------------------------------------------------------

    # --- Importações e Configurações que dependem do app ou extensões ---

    # Importa modelos AQUI, depois que 'db' existe mas antes dos blueprints
    from app import models
    # Importa especificamente StatusParcela para o context processor
    # (models já importa User, que importa login_manager para o user_loader)
    from app.models import StatusParcela

    # Context processor para injetar variáveis globais nos templates
    @app.context_processor
    def inject_global_vars():
        # Não precisa importar User aqui, a menos que use current_user diretamente
        return {
            'current_year': datetime.date.today().year,
            'generate_csrf': generate_csrf,
            'StatusParcela': StatusParcela,
            'date': date
        }

    # --- Registro dos Blueprints ---

    # Blueprint Principal ('main')
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp) # Registra sem prefixo (ou com prefixo se definido em routes.py)

    # Blueprint de Autenticação ('auth')
    from app.auth import bp as auth_bp # Importa o 'bp' definido em app/auth/__init__.py
    app.register_blueprint(auth_bp, url_prefix='/auth') # Registra com prefixo /auth

    # -----------------------------

    # O user_loader definido em models.py será associado ao login_manager
    # porque importamos 'login_manager' de 'app' dentro de models.py

    return app