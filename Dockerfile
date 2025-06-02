# Dockerfile

# 1. Escolha uma imagem base Python oficial
FROM python:3.13-slim-buster  # Ou a versão do Python que você está usando (ex: 3.9, 3.10)

# 2. Defina o diretório de trabalho dentro do container
WORKDIR /app

# 3. Copie o arquivo de dependências
COPY requirements.txt requirements.txt

# 4. Instale as dependências
# --no-cache-dir para reduzir o tamanho da imagem
# --upgrade pip para garantir a última versão do pip
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copie o restante do código da sua aplicação para o diretório de trabalho
COPY . .

# 6. Variáveis de Ambiente (Opcional - podem ser sobrescritas pelo Back4App)
# Você pode definir padrões aqui, mas é melhor configurar no Back4App
# ENV FLASK_APP wsgi:application  # Ou o nome do seu arquivo wsgi e variável da app
ENV FLASK_CONFIG production     # Exemplo, se você tiver uma ProductionConfig
# ENV PORT 8080 (O Back4App geralmente define a porta que seu container deve escutar)

# 7. Comando para rodar a aplicação quando o container iniciar
# O Back4App provavelmente injetará a variável de ambiente PORT.
# Gunicorn escutará em todas as interfaces (0.0.0.0).
# O número de workers pode ser ajustado. (2 * num_cores) + 1 é um bom ponto de partida.
# Use a variável de ambiente $PORT fornecida pela plataforma de hospedagem.
# Se o Back4App não fornecer $PORT, você pode precisar usar uma porta fixa como 8080 e mapeá-la.
CMD exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 3 --threads 2 wsgi:application