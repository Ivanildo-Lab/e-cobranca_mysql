# wsgi.py
from app import create_app
import os

# Cria a aplicação usando a configuração do ambiente ou um padrão
# Isso permite que você configure FLASK_CONFIG via variáveis de ambiente no Back4App
application = create_app(os.environ.get('FLASK_CONFIG') or 'default')

# Se você quiser que o app.run() ainda funcione para desenvolvimento local com `python wsgi.py`
# (embora `flask run` seja geralmente preferido para desenvolvimento)
# if __name__ == "__main__":
#     application.run()