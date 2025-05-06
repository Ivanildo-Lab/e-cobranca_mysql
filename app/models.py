# app/models.py
from datetime import datetime, date
from app import db # Importa a instância db criada em __init__.py
import enum,uuid,random
# app/models.py
# ... (outras importações) ...
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin # <-- Importar UserMixin
from app import db # (Já deve existir)
# Importa o login_manager que definiremos em __init__.py
# Fazemos isso aqui para definir o user_loader perto do modelo User
from app import login_manager # <-- Importar login_manager

# ... (Cidade, Cliente, Parcela, StatusParcela) ...

class User(UserMixin, db.Model): # <-- Herda de UserMixin e db.Model
    __tablename__ = 'tbl_users' # Nome da tabela
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256)) # Tamanho maior para hashes seguros
    is_admin = db.Column(db.Boolean, default=False) # Para futuras permissões
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        # Gera o hash da senha e armazena
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # Verifica se a senha fornecida corresponde ao hash armazenado
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# Função user_loader (exigida pelo Flask-Login)
# Diz ao Flask-Login como carregar um usuário dado o seu ID
@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id)) # Usa get para buscar pela PK


# Enum para o Status da Parcela
class StatusParcela(enum.Enum):
    ABERTA = 'Aberta'
    LIQUIDADA = 'Liquidada'
    CANCELADA = 'Cancelada' # Opcional

class Cidade(db.Model):
    __tablename__ = 'tbl_cidades'
    id = db.Column(db.Integer, primary_key=True)
    nome_cidade = db.Column(db.String(100), nullable=False, index=True)
    estado = db.Column(db.String(2), nullable=False, index=True) # Ex: SP, RJ

    # Relacionamento: Uma cidade pode ter muitos clientes
    clientes = db.relationship('Cliente', backref='cidade_ref', lazy='dynamic') # 'cidade_ref' será como acessaremos a cidade a partir de um cliente

    def __repr__(self):
        return f'<Cidade {self.nome_cidade}/{self.estado}>'

class Cliente(db.Model):
    __tablename__ = 'tbl_clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False, index=True)
    endereco = db.Column(db.String(255))
    telefone = db.Column(db.String(20), nullable=True) # Telefone (opcional)
    email = db.Column(db.String(150), nullable=True) # Email (opcional)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True) # Default=True (começa ativo)
    contato = db.Column(db.String(150)) # Nome da pessoa de contato (opcional)
    conexao = db.Column(db.String(100)) # Como conheceu, indicação, etc. (opcional)
    valor_mensalidade = db.Column(db.Numeric(10, 2), nullable=True) # Valor padrão (opcional)
    dia_cobranca = db.Column(db.Integer, nullable=True) # Dia do mês (1-31) (opcional)
    obs = db.Column(db.Text, nullable=True) # Campo de texto longo para observações
    data_cadastro = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    # Chave Estrangeira para Cidade
    cidade_id = db.Column(db.Integer, db.ForeignKey('tbl_cidades.id'), nullable=False)

    # Relacionamento: Um cliente pode ter muitas parcelas
    # cascade='all, delete-orphan' significa que ao deletar um cliente, suas parcelas também serão deletadas.
    parcelas = db.relationship('Parcela', backref='cliente_ref', lazy='dynamic', cascade='all, delete-orphan') # 'cliente_ref' será como acessaremos o cliente a partir de uma parcela

    def __repr__(self):
        return f'<Cliente {self.nome}>'
    
    def __repr__(self):
        status = "Ativo" if self.ativo else "Inativo"
        return f'<Cliente {self.nome} ({status})>'

class Parcela(db.Model):
    __tablename__ = 'tbl_parcelas'
    id = db.Column(db.Integer, primary_key=True)
    # --- Novo Campo Opcional ---
    cobranca_uuid = db.Column(db.String(36), index=True, nullable=True) # Para agrupar parcelas da mesma geração
    # --- Fim Novo Campo ---
    cliente_id = db.Column(db.Integer, db.ForeignKey('tbl_clientes.id'), nullable=False)
    numero_parcela = db.Column(db.String(20), nullable=False,index=True)
    total_parcelas = db.Column(db.Integer, nullable=False)
    valor_parcela = db.Column(db.Numeric(10, 2), nullable=False)
    data_geracao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_vencimento = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.Enum(StatusParcela), nullable=False, default=StatusParcela.ABERTA, index=True)
    data_pagamento = db.Column(db.Date, nullable=True)
    valor_pago = db.Column(db.Numeric(10, 2), nullable=True)

    # ... (Relacionamento e métodos __repr__, esta_vencida) ...
    # cliente_ref definido no backref do Cliente

    def __repr__(self):
        # Atualiza repr se adicionou cobranca_uuid
        uuid_str = f" (Cob: {self.cobranca_uuid[:8]}...)" if self.cobranca_uuid else ""
        return f'<Parcela {self.numero_parcela}/{self.total_parcelas} - Cliente ID: {self.cliente_id}{uuid_str} - Venc: {self.data_vencimento} - Status: {self.status.value}>'
   
    @property
    def esta_vencida(self):
        # Verifica se a parcela está aberta e a data de vencimento passou
        return self.status == StatusParcela.ABERTA and self.data_vencimento < date.today()