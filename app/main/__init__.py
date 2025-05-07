# app/main/__init__.py
from flask import Blueprint

bp = Blueprint('main', __name__)

from . import routes  # Importa o routes.py do mesmo diretório (app/main/)
# Se você tiver forms.py em app/main/ e ele precisar ser parte da inicialização do bp, importe aqui também
# Exemplo: from . import forms