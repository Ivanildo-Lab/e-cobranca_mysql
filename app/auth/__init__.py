# app/auth/__init__.py
from flask import Blueprint

# Define o Blueprint para a autenticação
# O primeiro argumento 'auth' é o nome do blueprint, usado em url_for('auth.rota')
# O segundo argumento __name__ ajuda o Flask a localizar templates e arquivos estáticos
bp = Blueprint('auth', __name__) 

# Importa as rotas e formulários DEPOIS da criação do blueprint 'bp'
# Isso evita problemas de importação circular, pois routes.py e forms.py
# podem precisar importar 'bp' deste arquivo.
# Usamos importações relativas (com '.') porque routes e forms estão no mesmo pacote 'auth'.
from . import routes, forms