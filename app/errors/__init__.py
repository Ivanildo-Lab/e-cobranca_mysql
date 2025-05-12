# app/errors/__init__.py
from flask import Blueprint

bp = Blueprint('errors', __name__)

from . import handlers  # Importa o handlers.py do mesmo diretório