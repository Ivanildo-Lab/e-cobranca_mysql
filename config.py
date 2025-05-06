# config.py
import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env para o ambiente
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '4352804620cf8327a237b47994180a7aa3f5158dd8f88670b94e9a3c6d93415c05ec658f92e179a0dd56856ee5445a8df8644c49ac484c37151a9f172fa6b95967f9681a3ed817f79d531babe49f5e4632fb9e040d6bca19b87ef6a1eaef9aa2612f3692a0eca0a4f51c3ce3e64fdd26b80d842d3515f16e889d0a417b6f71a45e2f913ee145e81a0b398b5ccbc3ece65331a20faafc1c880af091f2408214268a2f7d0d43fb7b8cd75330d563325fc1734bfea75be559d90967844560934f62eaf79625b80e9544b88be804983feed49143a403eb9386236fe89558be5e6ca27ae00b0d389c619d240f7ecd745b5eda7f896483cc076cf4cafa61a51065fcd8'
    # Configuração do Banco de Dados PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:1234@localhost/ecobrancas_db' # Substitua com seus dados
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Desativa warnings desnecessários