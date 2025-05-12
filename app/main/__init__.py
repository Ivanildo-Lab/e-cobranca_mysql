# app/main/__init__.py
from flask import Blueprint

# Define o Blueprint 'main'. Este é o objeto 'bp' que será importado
# pelo app/__init__.py principal e pelo routes.py dentro deste pacote.
bp = Blueprint('main', __name__)

# Importa as rotas DEPOIS da definição do bp para evitar ciclos de importação.
# As rotas definidas em routes.py usarão este 'bp'.
from . import routes