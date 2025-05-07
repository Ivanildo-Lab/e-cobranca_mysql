# app/errors/handlers.py
from flask import render_template
# REMOVIDO: from flask_babel import _
from app import db
from . import bp # app.errors.bp (ou app.errors import bp as errors_bp se você renomeou)

@bp.app_errorhandler(404)
def not_found_error(error):
    # Texto simples para title
    return render_template('errors/404.html', title='Page Not Found'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    # Texto simples para title
    return render_template('errors/500.html', title='Internal Server Error'), 500