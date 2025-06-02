# .flaskenv (na pasta /home/seuusername/e-cobranca/)
FLASK_APP=run.py  # Ou o nome do seu arquivo de entrada principal
# FLASK_DEBUG=0 # Desabilitar debug em produção
# As variáveis DATABASE_URL e SECRET_KEY serão lidas pelo config.py a partir do .env se load_dotenv estiver lá.
# Ou, para garantir que o CLI use as mesmas do WSGI, você pode precisar exportá-las no console
# antes de rodar os comandos flask db, ou garantir que seu config.py consiga achá-las.