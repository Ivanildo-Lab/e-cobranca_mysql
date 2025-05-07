# app/__init__.py
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from flask import Flask # request, current_app não são mais usados globalmente aqui após remover Babel e g.locale
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap4 as Bootstrap
from flask_moment import Moment
# REMOVIDO: from flask_babel import Babel, lazy_gettext as _l
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
bootstrap = Bootstrap()
moment = Moment()
# REMOVIDO: babel = Babel()

@login_manager.user_loader
def load_user(user_id):
    from app.models import User # Importação local para evitar ciclos
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    # REMOVIDO: babel.init_app(app)

    login_manager.login_view = 'auth.login'
    # Texto simples, sem _l()
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # REMOVIDA: Definição de get_locale_for_request e registro com babel

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    if not app.debug and not app.testing:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'], # Ajuste o email do remetente se necessário
                toaddrs=app.config['ADMINS'], subject='e-Cobranca Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/e_cobranca.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('e-Cobranca startup')

    return app