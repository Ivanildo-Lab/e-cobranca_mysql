# app/forms.py
from flask_wtf import FlaskForm
# Adicione os novos tipos de campo e validadores necessários
from wtforms import StringField, SubmitField, SelectField, TextAreaField, BooleanField, DecimalField, IntegerField
from wtforms.validators import InputRequired, DataRequired, Length, Optional, NumberRange # Adicione Optional e NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField
from app.models import Cidade
from wtforms.fields.datetime import DateField
from app.models import Cliente # Importa Cliente
from app.models import Cliente, Cidade # Precisa de Cidade agora
from app.models import StatusParcela # Importa o Enum diretamente


class CidadeForm(FlaskForm):
    nome_cidade = StringField('Nome da Cidade', validators=[DataRequired(), Length(min=2, max=100)])
    # Lista de UFs (pode ser expandida ou carregada de outro lugar se necessário)
    estados_brasileiros = [
        ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'), ('BA', 'BA'),
        ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'), ('GO', 'GO'), ('MA', 'MA'),
        ('MT', 'MT'), ('MS', 'MS'), ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'),
        ('PR', 'PR'), ('PE', 'PE'), ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'),
        ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), ('SC', 'SC'), ('SP', 'SP'),
        ('SE', 'SE'), ('TO', 'TO')
    ]
    estado = SelectField('Estado (UF)', choices=estados_brasileiros, validators=[DataRequired()])
    submit = SubmitField('Salvar Cidade')

# Função para obter as opções do QuerySelectField (Cidades)
def get_cidades():
    # Retorna todas as cidades ordenadas por nome para o dropdown
    return Cidade.query.order_by(Cidade.nome_cidade).all()

# Função para obter o label (texto exibido) de cada cidade no dropdown
def get_cidade_label(cidade):
    return f"{cidade.nome_cidade}/{cidade.estado}"

class ClienteForm(FlaskForm):
    nome = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=150)])
    endereco = TextAreaField('Endereço Completo', validators=[Length(max=255)]) # TextArea para mais espaço
    cidade = QuerySelectField('Cidade',
                              query_factory=get_cidades,
                              get_label=get_cidade_label,
                              allow_blank=False,
                              validators=[DataRequired(message="Selecione uma cidade.")])
    contato = StringField('Pessoa de Contato', validators=[Optional(), Length(max=150)])
    conexao = StringField('Tipo de Conexão/Relacionamento', validators=[Optional(), Length(max=100)])
    telefone = TextAreaField('Telefone/Celular', validators=[Length(max=255)]) # TextArea para mais espaço
    email = StringField('Email', validators=[Optional(), Length(max=150)]) # Email (opcional)
    # QuerySelectField para buscar cidades do banco
    # query_factory: função que retorna a lista de opções
    # get_label: função ou nome do atributo que define o texto exibido
    # allow_blank: se permite não selecionar nada (vamos deixar False, cidade é obrigatória)
    # blank_text: texto para a opção em branco (se allow_blank=True)
    valor_mensalidade = DecimalField('Valor Mensalidade Padrão (R$)',
                                     places=2, # Duas casas decimais
                                     validators=[Optional()]) # Permite campo vazio
    dia_cobranca = IntegerField('Dia Padrão para Cobrança (1-31)',
                                validators=[Optional(),
                                            NumberRange(min=1, max=31, message="Dia deve ser entre 1 e 31.")])
    obs = TextAreaField('Observações', validators=[Optional()])
    ativo = BooleanField('Cliente Ativo?', default=True) # Checkbox (marcado por padrão)

  
    submit = SubmitField('Salvar Cliente')

# Definir o Formulário de Geração de Parcelas 
# Função para obter clientes ativos para o select
def get_clientes_ativos():
    return Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()

class GerarParcelasForm(FlaskForm):
    cliente = QuerySelectField('Selecione o Cliente',
                               query_factory=get_clientes_ativos,
                               get_label='nome', # Mostra o nome do cliente no select
                               allow_blank=False,
                               validators=[DataRequired(message="Selecione um cliente.")])
    valor_parcela = DecimalField('Valor de Cada Parcela (R$)',
                                 places=2,
                                 validators=[DataRequired(message="Valor da parcela é obrigatório."),
                                             NumberRange(min=0.01, message="Valor deve ser positivo.")])
    quantidade_parcelas = IntegerField('Quantidade de Parcelas',
                                       validators=[DataRequired(message="Quantidade é obrigatória."),
                                                   NumberRange(min=1, message="Deve haver pelo menos 1 parcela.")])
    # Usamos DateField para a data de vencimento
    primeiro_vencimento = DateField('Data do Primeiro Vencimento',
                                    format='%Y-%m-%d', # Formato esperado pelo HTML5 date input
                                    validators=[DataRequired(message="Data do primeiro vencimento é obrigatória.")])
    # Campo para periodicidade (poderia ser expandido)
    periodicidade = SelectField('Periodicidade',
                                choices=[('mensal', 'Mensal')], # Começando com mensal
                                validators=[DataRequired()])
    submit = SubmitField('Gerar Parcelas')

# Definir o Formulário de Registro de Pagamento
class RegistrarPagamentoForm(FlaskForm):
    data_pagamento = DateField('Data do Pagamento',
                               format='%Y-%m-%d',
                               validators=[InputRequired(message="Data do pagamento é obrigatória.")],
                               # Podemos sugerir a data atual usando 'default'
                               # mas o WTForms pode ter problemas com default=date.today
                               # É mais fácil fazer isso no HTML ou com JS.
                               # default=date.today
                               )
    valor_pago = DecimalField('Valor Pago (R$)',
                              places=2,
                              validators=[InputRequired(message="Valor pago é obrigatório."),
                                          NumberRange(min=0.01, message="Valor deve ser positivo.")])
    submit = SubmitField('Confirmar Pagamento')

# Definir o Formulário de Edição de Parcela
# Este formulário será usado para editar parcelas já existentes
class EditarParcelaForm(FlaskForm):
    # Não vamos editar cliente, nº parcela, total, etc.
    valor_parcela = DecimalField('Valor da Parcela (R$)',
                                 places=2,
                                 validators=[InputRequired(message="Valor é obrigatório."),
                                             NumberRange(min=0.01, message="Valor deve ser positivo.")])
    data_vencimento = DateField('Data de Vencimento',
                                format='%Y-%m-%d',
                                validators=[InputRequired(message="Data de vencimento é obrigatória.")])
    # Opcional: Campo para observação/justificativa da edição
    # obs_edicao = TextAreaField('Observação da Edição', validators=[Optional()])
    submit = SubmitField('Salvar Alterações')


class SelecionarClienteForm(FlaskForm):
    cliente = QuerySelectField('Cliente',
                               query_factory=get_clientes_ativos,
                               get_label='nome',
                               allow_blank=False,
                               validators=[DataRequired()])
    # --- NOVOS CAMPOS DE DATA ---
    # Tornamos opcionais, pois o usuário pode querer o extrato completo
    data_inicio = DateField('Data Inicial (Vencimento)',
                            format='%Y-%m-%d',
                            validators=[Optional()])
    data_fim = DateField('Data Final (Vencimento)',
                         format='%Y-%m-%d',
                         validators=[Optional()])
    # --- FIM NOVOS CAMPOS ---
    submit = SubmitField('Ver Extrato / Aplicar Filtros') # Texto do botão atualizado
# app/forms.py
# ... (imports, DateField, Optional) ...

# ... (Outros formulários) ...

# app/forms.py
# ... (imports: FlaskForm, QuerySelectField, DateField, SelectField, SubmitField, Optional, DataRequired) ...
from app.models import Cliente, Cidade # Precisa de Cidade agora
from app.models import StatusParcela # Importa o Enum diretamente

# Funções 'get_cidades' e 'get_clientes_ativos' já devem existir

class FiltroParcelasForm(FlaskForm):
    status = SelectField('Status',
                         choices=[ # Define as opções aqui
                             ('todas', 'Todas'),
                             ('aberta', 'Abertas (Não Vencidas)'),
                             ('liquidada', 'Liquidadas'),
                             ('atrasada', 'Atrasadas'),
                             ('cancelada', 'Canceladas')
                         ],
                         default='aberta', # Define o padrão
                         validators=[Optional()]) # Opcional, pois tem default

    cliente = QuerySelectField('Cliente',
                               query_factory=get_clientes_ativos,
                               get_label='nome',
                               allow_blank=True, # Permite selecionar "Todos"
                               blank_text='-- Todos os Clientes --',
                               validators=[Optional()]) # Opcional

    # --- NOVO CAMPO CIDADE ---
    cidade = QuerySelectField('Cidade',
                              query_factory=get_cidades, # Reusa a função
                              get_label=get_cidade_label, # Reusa a função
                              allow_blank=True, # Permite "Todas"
                              blank_text='-- Todas as Cidades --',
                              validators=[Optional()]) # Opcional
    # --- FIM NOVO CAMPO ---

    venc_inicio = DateField('Vencimento (Início)', format='%Y-%m-%d', validators=[Optional()])
    venc_fim = DateField('Vencimento (Fim)', format='%Y-%m-%d', validators=[Optional()])
    pag_inicio = DateField('Pagamento (Início)', format='%Y-%m-%d', validators=[Optional()])
    pag_fim = DateField('Pagamento (Fim)', format='%Y-%m-%d', validators=[Optional()])

    submit = SubmitField('Filtrar')

    # Adicionaremos mais formulários aqui depois 