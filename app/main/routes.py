# app/routes.py
from flask import  render_template, request, flash, redirect, url_for
from app import db
from sqlalchemy.orm import joinedload
from datetime import date, datetime , timedelta # Garanta que datetime e date estão importados
from dateutil.relativedelta import relativedelta # Importa relativedelta
import uuid,random # Importa uuid se for usar cobranca_uuid
from app.models import Parcela, StatusParcela, Cliente,Parcela, StatusParcela,Cidade # Garanta que Parcela e StatusParcela estão aqui
from sqlalchemy import or_, and_ , func, extract # Importa 'and_' se for combinar condições complexas
from app.forms import (CidadeForm, ClienteForm, GerarParcelasForm,
                       RegistrarPagamentoForm, EditarParcelaForm,FiltroParcelasForm)
import locale # Para formatação de datas em português
# ... (Blueprint e outras rotas) ...
from decimal import Decimal # Para garantir que valores monetários sejam tratados corretamente
from flask import make_response # <-- Adicionar
from weasyprint import HTML, CSS # <-- Adicionar
from flask_login import login_required # Adiciona importação para proteger rotas
from . import bp # Importa o Blueprint 'bp' definido em __init__.py

# Cria um Blueprint chamado 'main' (pode ter outro nome)
# O primeiro argumento é o nome do Blueprint
# O segundo é o nome do módulo ou pacote onde o Blueprint está localizado (__name__)
# O terceiro (opcional) define um prefixo de URL para todas as rotas do Blueprint


# Rota para a página inicial (exemplo, pode ser um dashboard depois)
@bp.route('/')
@bp.route('/index')
@bp.route('/dashboard') # Adiciona alias /dashboard
@login_required # Protege a rota, requer login
def dashboard():
    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    hoje = date.today()
    mes_atual_num = hoje.month # Pega o número do mês
    ano_atual = hoje.year
    # ... (outros cálculos de data) ...

    # --- Mapeamento de Mês ---
    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    nome_mes_atual = meses_pt.get(mes_atual_num, str(mes_atual_num)) # Pega nome ou número se der erro
    mes_ano_formatado = f"{nome_mes_atual}/{ano_atual}"
    # -------------------------

    # 1. A Receber no Mês Atual
    a_receber_mes_atual = db.session.query(func.sum(Parcela.valor_parcela)) \
                            .join(Cliente, Parcela.cliente_id == Cliente.id) \
                            .filter(Cliente.ativo == True,
                                    Parcela.status == StatusParcela.ABERTA,
                                    extract('year', Parcela.data_vencimento) == ano_atual,
                                    extract('month', Parcela.data_vencimento) == mes_atual).scalar() or 0.0

    # 2. Recebido nos Últimos 30 Dias
    recebido_30_dias = db.session.query(func.sum(Parcela.valor_pago)) \
                         .join(Cliente, Parcela.cliente_id == Cliente.id) \
                         .filter(Cliente.ativo == True,
                                 Parcela.status == StatusParcela.LIQUIDADA,
                                    extract('year', Parcela.data_vencimento) == ano_atual,
                                    extract('month', Parcela.data_vencimento) == mes_atual).scalar() or 0.0

    # 3. Total Atrasado
    total_atrasado = db.session.query(func.sum(Parcela.valor_parcela)) \
                       .join(Cliente, Parcela.cliente_id == Cliente.id) \
                       .filter(Cliente.ativo == True,
                               Parcela.status == StatusParcela.ABERTA,
                               Parcela.data_vencimento < hoje).scalar() or 0.0

    
    # --- Dados para o Gráfico (Ex: Recebido vs A Vencer últimos 6 meses) ---
    labels_chart = []
    data_recebido_chart = []
    data_a_vencer_chart = []

    for i in range(5, -1, -1): # Loop de 6 meses atrás até o mês atual
        mes_referencia = hoje - relativedelta(months=i)
        mes_str = mes_referencia.strftime("%m/%Y")
        labels_chart.append(mes_str)
        ano_ref = mes_referencia.year
        mes_ref = mes_referencia.month

        # Query base para clientes ativos (repetida aqui para clareza no gráfico)
        base_chart_query = Parcela.query.join(Cliente, Parcela.cliente_id == Cliente.id).filter(Cliente.ativo == True)

        # A Vencer no mês
        a_vencer_mes = db.session.query(func.sum(Parcela.valor_parcela)).select_from(base_chart_query) \
                        .filter(Parcela.status == StatusParcela.ABERTA,
                                extract('year', Parcela.data_vencimento) == ano_ref,
                                extract('month', Parcela.data_vencimento) == mes_ref).scalar() or 0.0
        data_a_vencer_chart.append(float(a_vencer_mes))

        # Recebido no mês
        recebido_mes = db.session.query(func.sum(Parcela.valor_pago)).select_from(base_chart_query) \
                         .filter(Parcela.status == StatusParcela.LIQUIDADA,
                                 extract('year', Parcela.data_pagamento) == ano_ref,
                                 extract('month', Parcela.data_pagamento) == mes_ref).scalar() or 0.0
        data_recebido_chart.append(float(recebido_mes))

    chart_data = {
        'labels': labels_chart,
        'datasets': [
             {'label': 'Valor Recebido', 'backgroundColor': 'rgba(75, 192, 192, 0.5)', 'borderColor': 'rgb(75, 192, 192)', 'data': data_recebido_chart, 'borderWidth': 1},
             {'label': 'Valor a Vencer', 'backgroundColor': 'rgba(255, 159, 64, 0.5)', 'borderColor': 'rgb(255, 159, 64)', 'data': data_a_vencer_chart, 'borderWidth': 1}
        ]
    }

    return render_template(
        'dashboard/index.html',
        title='Dashboard',
        # Novos/Ajustados valores para os cards
        mes_ano_atual=hoje.strftime("%m/%Y"), # Passa MM/YYYY atual
        a_receber_mes_atual=a_receber_mes_atual,
        recebido_30_dias=recebido_30_dias,
        total_atrasado=total_atrasado,
        nome_mes_atual=mes_ano_formatado, # Passa o mês/ano formatado
        chart_data=chart_data
    )

# Rota para LISTAR Cidades
@bp.route('/cidades')
@bp.route('/cidades/lista')
def listar_cidades():
    page = request.args.get('page', 1, type=int) # Pega o número da página da URL, default é 1
    # Busca cidades ordenadas por nome e pagina o resultado (ex: 10 por página)
    cidades = Cidade.query.order_by(Cidade.nome_cidade).paginate(page=page, per_page=10)
    return render_template('cidades/lista_cidades.html', cidades=cidades, title='Lista de Cidades')

# Rota para ADICIONAR Nova Cidade (GET para mostrar formulário, POST para processar)
@bp.route('/cidades/novo', methods=['GET', 'POST'])
@login_required # Protege a rota, requer login
def adicionar_cidade():
    form = CidadeForm()
    if form.validate_on_submit(): # Valida o formulário no POST
        # Cria uma nova instância do modelo Cidade com os dados do formulário
        nova_cidade = Cidade(nome_cidade=form.nome_cidade.data, estado=form.estado.data)
        db.session.add(nova_cidade) # Adiciona ao banco de dados (ainda não salva)
        try:
            db.session.commit() # Salva as mudanças no banco
            flash(f'Cidade "{nova_cidade.nome_cidade}/{nova_cidade.estado}" adicionada com sucesso!', 'success')
            return redirect(url_for('main.listar_cidades')) # Redireciona para a lista
        except Exception as e:
            db.session.rollback() # Desfaz em caso de erro
            flash(f'Erro ao adicionar cidade: {e}', 'danger')
    # Se for GET ou se o formulário não for válido, renderiza o template do formulário
    return render_template('cidades/form_cidade.html', form=form, title='Adicionar Nova Cidade', legend='Nova Cidade')

# Rota para EDITAR Cidade Existente (GET para mostrar form preenchido, POST para processar)
@bp.route('/cidades/<int:id>/editar', methods=['GET', 'POST'])
@login_required # Protege a rota, requer login
def editar_cidade(id):
    cidade = db.get_or_404(Cidade, id) # Busca a cidade pelo ID ou retorna erro 404
    form = CidadeForm(obj=cidade) # Pré-popula o formulário com os dados da cidade

    if form.validate_on_submit():
        # Atualiza os campos da cidade com os dados do formulário
        cidade.nome_cidade = form.nome_cidade.data
        cidade.estado = form.estado.data
        try:
            db.session.commit() # Salva as alterações
            flash(f'Cidade "{cidade.nome_cidade}/{cidade.estado}" atualizada com sucesso!', 'success')
            return redirect(url_for('main.listar_cidades'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar cidade: {e}', 'danger')
    # Se for GET, mostra o formulário preenchido
    return render_template('cidades/form_cidade.html', form=form, title='Editar Cidade', legend=f'Editando: {cidade.nome_cidade}')

# Rota para DELETAR Cidade (usaremos POST para segurança)
@bp.route('/cidades/<int:id>/deletar', methods=['POST'])
@login_required # Protege a rota, requer login
def deletar_cidade(id):
    cidade = db.get_or_404(Cidade, id)

    # Verifica se existem clientes associados a esta cidade antes de deletar
    if cidade.clientes.first(): # .first() é eficiente, não carrega todos os clientes
         flash(f'Não é possível excluir a cidade "{cidade.nome_cidade}/{cidade.estado}" pois existem clientes cadastrados nela.', 'warning')
         return redirect(url_for('main.listar_cidades'))

    try:
        nome_cidade_deletada = f"{cidade.nome_cidade}/{cidade.estado}"
        db.session.delete(cidade) # Marca para deleção
        db.session.commit() # Efetiva a deleção
        flash(f'Cidade "{nome_cidade_deletada}" excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir cidade: {e}', 'danger')
    return redirect(url_for('main.listar_cidades'))

# --- ROTAS DE CLIENTES ---

@bp.route('/clientes')
@login_required # Protege a rota, requer login
def listar_clientes():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    # --- Pega o filtro de status, default 'ativos' ---
    status_filter = request.args.get('status', 'ativos')

    query = Cliente.query.options(joinedload(Cliente.cidade_ref)) # Query base

    # --- Aplica filtro de STATUS ---
    if status_filter == 'ativos':
        query = query.filter(Cliente.ativo == True)
    elif status_filter == 'inativos':
        query = query.filter(Cliente.ativo == False)
    # Se for 'todos', nenhum filtro de status é aplicado
    # --- FIM Filtro STATUS ---

    # Aplica filtro de BUSCA (depois do status)
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Cliente.nome.ilike(search_term),
                Cliente.contato.ilike(search_term)
            )
        )

    # Ordenação e paginação
    clientes = query.order_by(Cliente.nome).paginate(page=page, per_page=10, error_out=False)

    # Passa clientes paginados para o template
    # O template acessa 'q' e 'status' diretamente de 'request.args'
    return render_template('clientes/lista_clientes.html', clientes=clientes, title='Lista de Clientes')

# ... (rotas adicionar_cliente, editar_cliente, deletar_cliente) ...
# Rota para ADICIONAR Novo Cliente
@bp.route('/clientes/novo', methods=['GET', 'POST'])
@login_required # Protege a rota, requer login
def adicionar_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        novo_cliente = Cliente(
            nome=form.nome.data,
            contato=form.contato.data,
            conexao=form.conexao.data,
            endereco=form.endereco.data,
            cidade_id=form.cidade.data.id,
            telefone=form.telefone.data,
            email=form.email.data,
            valor_mensalidade=form.valor_mensalidade.data,
            dia_cobranca=form.dia_cobranca.data,
            obs=form.obs.data,
            ativo=form.ativo.data  
        )
        db.session.add(novo_cliente)
        try:
            db.session.commit()
            flash(f'Cliente "{novo_cliente.nome}" adicionado com sucesso!', 'success')
            return redirect(url_for('main.listar_clientes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar cliente: {e}', 'danger')
    return render_template('clientes/form_cliente.html', form=form, title='Adicionar Novo Cliente', legend='Novo Cliente')

# Rota para EDITAR Cliente Existente
@bp.route('/clientes/<int:id>/editar', methods=['GET', 'POST'])
@login_required # Protege a rota, requer login
def editar_cliente(id):
    cliente = db.get_or_404(Cliente, id)
    # Pré-popula o formulário com dados do objeto cliente (incluindo os novos campos)
    form = ClienteForm(obj=cliente)

    # Garante que a cidade correta esteja selecionada no GET (ainda necessário para QuerySelectField)
    if request.method == 'GET':
         form.cidade.data = cliente.cidade_ref

    if form.validate_on_submit():
        # Atualiza todos os campos do cliente com os dados do formulário
        cliente.nome = form.nome.data
        cliente.endereco = form.endereco.data
        cliente.cidade_id = form.cidade.data.id
        # --- Atualizando novos campos ---
        cliente.ativo = form.ativo.data
        cliente.contato = form.contato.data
        cliente.conexao = form.conexao.data
        cliente.valor_mensalidade = form.valor_mensalidade.data
        cliente.dia_cobranca = form.dia_cobranca.data
        cliente.obs = form.obs.data
        # --- Fim novos campos ---
        try:
            db.session.commit()
            flash(f'Cliente "{cliente.nome}" atualizado com sucesso!', 'success')
            return redirect(url_for('main.listar_clientes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar cliente: {e}', 'danger')

    return render_template('clientes/form_cliente.html', form=form, title='Editar Cliente', legend=f'Editando: {cliente.nome}')

# Rota para DESATIVAR Cliente (antiga deletar_cliente)

@bp.route('/clientes/<int:id>/desativar', methods=['POST'])
@login_required # Protege a rota, requer login
def desativar_cliente(id):
    cliente = db.get_or_404(Cliente, id)


    try:
        nome_cliente_desativado = cliente.nome
        # --- LÓGICA PRINCIPAL: Mudar o status para False ---
        cliente.ativo = False
        db.session.commit() # Salva a alteração do status
        # --- FIM LÓGICA PRINCIPAL ---
        flash(f'Cliente "{nome_cliente_desativado}" desativado com sucesso!', 'success') # Mensagem atualizada
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao desativar cliente: {e}', 'danger') # Mensagem atualizada
    return redirect(url_for('main.listar_clientes'))

# --- ROTA PARA GERAR PARCELAS ---
@bp.route('/cobrancas/gerar', methods=['GET', 'POST'])
@login_required # Protege a rota, requer login
def gerar_parcelas():
    form = GerarParcelasForm()
    if form.validate_on_submit():
        cliente_selecionado = form.cliente.data # Objeto Cliente
        valor = form.valor_parcela.data
        quantidade = form.quantidade_parcelas.data
        primeira_data = form.primeiro_vencimento.data # Já é um objeto date
        periodicidade = form.periodicidade.data
        data_geracao = datetime.utcnow() # Data/Hora atual para todas as parcelas geradas
        cobranca_id_unico = str(uuid.uuid4()) # Gera um ID único para este lote de parcelas (se usar o campo)
        random_part = random.randint(100000, 999999) # Gera um número de 6 dígitos
        try:
            for i in range(quantidade):
                numero_sequencial = i + 1 # Sequencial da parcela (1, 2, 3...)
                data_vencimento_parcela = primeira_data

                # Calcula próxima data de vencimento (exceto para a primeira)
                if i > 0:
                    if periodicidade == 'mensal':
                        # Adiciona 'i' meses à primeira data
                        data_vencimento_parcela = primeira_data + relativedelta(months=i)
                    # Adicionar outras lógicas de periodicidade aqui (quinzenal, semanal, etc.)
                    # elif periodicidade == 'quinzenal':
                    #    data_vencimento_parcela = primeira_data + relativedelta(days=15*i) # Exemplo simples
 
               # --- CONSTRÓI O NÚMERO DA PARCELA FORMATADO ---
                numero_parcela_formatado = f"{random_part}-{numero_sequencial}/{quantidade}"
                # --- FIM CONSTRUÇÃO ---

                # Cria a instância da Parcela
                nova_parcela = Parcela(
                    cobranca_uuid=cobranca_id_unico, # Atribui o ID do lote (se usar)
                    cliente_id=cliente_selecionado.id,
                    numero_parcela=numero_parcela_formatado,
                    total_parcelas=quantidade,
                    valor_parcela=valor,
                    data_geracao=data_geracao,
                    data_vencimento=data_vencimento_parcela,
                    status=StatusParcela.ABERTA # Status inicial
                    # data_pagamento e valor_pago ficam nulos
                )
                db.session.add(nova_parcela)

            db.session.commit() # Salva todas as parcelas geradas no banco
            flash(f'{quantidade} parcelas geradas com sucesso para o cliente {cliente_selecionado.nome}!', 'success')
            # Redireciona para a lista de clientes ou para uma futura lista de parcelas
            return redirect(url_for('main.listar_clientes')) # Ou 'main.listar_parcelas'

        except Exception as e:
            db.session.rollback() # Desfaz tudo em caso de erro
            flash(f'Erro ao gerar parcelas: {e}', 'danger')

    # Se for GET ou o formulário for inválido
    return render_template('cobrancas/gerar_parcelas.html', form=form, title='Gerar Novas Parcelas')


# --- ROTA PARA REGISTRAR PAGAMENTO ---

# app/routes.py
# ... (outras importações) ...
# Adiciona o novo formulário
from app.forms import CidadeForm, ClienteForm, GerarParcelasForm, RegistrarPagamentoForm

# ... (Blueprint e outras rotas) ...

# --- ROTA PARA REGISTRAR PAGAMENTO ---
# Recebe o ID da parcela na URL e só aceita POST
@bp.route('/parcelas/<int:id>/pagar', methods=['POST'])
@login_required # Protege a rota, requer login
def registrar_pagamento(id):
    parcela = db.get_or_404(Parcela, id) # Busca a parcela específica

    # Segurança: Verifica se a parcela realmente está aberta antes de pagar
    if parcela.status != StatusParcela.ABERTA:
        flash('Esta parcela não está aberta para pagamento.', 'warning')
        return redirect(url_for('main.listar_parcelas')) # Ou de onde veio

    form = RegistrarPagamentoForm() # Instancia o formulário

    # O WTForms valida os dados recebidos do POST automaticamente aqui
    if form.validate_on_submit():
        try:
            # Atualiza os campos da parcela com os dados do formulário
            parcela.data_pagamento = form.data_pagamento.data
            parcela.valor_pago = form.valor_pago.data
            parcela.status = StatusParcela.LIQUIDADA # Muda o status

            db.session.commit() # Salva as alterações no banco
            flash(f'Pagamento da parcela {parcela.numero_parcela} registrado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback() # Desfaz em caso de erro
            flash(f'Erro ao registrar pagamento: {e}', 'danger')
    else:
        # Se a validação do formulário falhar (ex: data inválida, valor não numérico)
        # Captura os erros para exibir
        erros = []
        for field, error_list in form.errors.items():
            erros.extend(error_list)
        flash('Erro ao processar pagamento: ' + '; '.join(erros), 'danger')


    # Redireciona de volta para a lista de parcelas (poderia ser a página anterior)
    # Idealmente, manteria os filtros da página anterior, mas isso é mais complexo
    return redirect(url_for('main.listar_parcelas'))

# --- ROTA PARA CANCELAR PARCELA ---
@bp.route('/parcelas/<int:id>/cancelar', methods=['POST'])
@login_required # Protege a rota, requer login
def cancelar_parcela(id):
    parcela = db.get_or_404(Parcela, id)

    # Permite cancelar apenas parcelas ABERTAS (não pagas)
    if parcela.status != StatusParcela.ABERTA:
        flash('Apenas parcelas abertas podem ser canceladas.', 'warning')
        return redirect(url_for('main.listar_parcelas')) # Idealmente, manter filtros

    try:
        parcela.status = StatusParcela.CANCELADA # Muda o status
        # Opcional: Limpar dados de pagamento se houver por algum erro? Geralmente não.
        # parcela.data_pagamento = None
        # parcela.valor_pago = None
        db.session.commit()
        flash(f'Parcela {parcela.numero_parcela} cancelada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao cancelar parcela: {e}', 'danger')

    return redirect(url_for('main.listar_parcelas')) # Idealmente, manter filtros

# --- ROTA PARA EDITAR PARCELA ---
@bp.route('/parcelas/<int:id>/editar', methods=['GET', 'POST'])
@login_required # Protege a rota, requer login
def editar_parcela(id):
    parcela = db.get_or_404(Parcela, id)

    # Permite editar apenas parcelas ABERTAS
    if parcela.status != StatusParcela.ABERTA:
        flash('Apenas parcelas abertas podem ser editadas.', 'warning')
        return redirect(url_for('main.listar_parcelas')) # Idealmente, manter filtros

    form = EditarParcelaForm(obj=parcela) # Pré-popula com dados atuais

    if form.validate_on_submit():
        try:
            parcela.valor_parcela = form.valor_parcela.data
            parcela.data_vencimento = form.data_vencimento.data
            # parcela.obs_edicao = form.obs_edicao.data # Se adicionar campo obs
            db.session.commit()
            flash(f'Parcela {parcela.numero_parcela} atualizada com sucesso!', 'success')
            return redirect(url_for('main.listar_parcelas')) # Idealmente, manter filtros
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar parcela: {e}', 'danger')

    # Se for GET ou form inválido, renderiza o template de edição
    return render_template('cobrancas/form_editar_parcela.html',
                           title='Editar Parcela',
                           form=form,
                           parcela=parcela) # Passa a parcela para exibir infos

# --- FIM DA ROTA EDITAR PARCELA ---


# --- ROTA PARA LISTAR PARCELAS ---
@bp.route('/parcelas')
@bp.route('/parcelas/lista')
def listar_parcelas():
    page = request.args.get('page', 1, type=int)
    # Instancia o formulário com dados da URL GET
    form = FiltroParcelasForm(request.args)

    # --- Leitura dos Filtros a partir do form (ou args como fallback) ---
    # Usa form.data se disponível, senão pega de request.args com defaults
    status_filter = form.status.data or request.args.get('status', 'aberta')
    cliente_filter = form.cliente.data # Será o objeto Cliente ou None
    cidade_filter = form.cidade.data   # Será o objeto Cidade ou None
    venc_inicio_f = form.venc_inicio.data
    venc_fim_f = form.venc_fim.data
    pag_inicio_f = form.pag_inicio.data
    pag_fim_f = form.pag_fim.data

    # Query base - JOINs movidos para dentro dos filtros condicionais
    query = Parcela.query.options(joinedload(Parcela.cliente_ref).joinedload(Cliente.cidade_ref)) # Carrega cliente e cidade

    # Aplica filtro inicial para Clientes Ativos SEMPRE
    query = query.join(Cliente, Parcela.cliente_id == Cliente.id).filter(Cliente.ativo == True)

    # --- Aplicação dos Filtros ---
    # 1. Filtro por Status
    hoje = date.today()
    if status_filter == 'aberta':
        query = query.filter(Parcela.status == StatusParcela.ABERTA, Parcela.data_vencimento >= hoje)
    elif status_filter == 'liquidada':
        query = query.filter(Parcela.status == StatusParcela.LIQUIDADA)
    elif status_filter == 'atrasada':
        query = query.filter(Parcela.status == StatusParcela.ABERTA, Parcela.data_vencimento < hoje)
    elif status_filter == 'cancelada':
         query = query.filter(Parcela.status == StatusParcela.CANCELADA)
    # Se 'todas', nenhum filtro de status aqui

    # 2. Filtro por Cliente Específico
    if cliente_filter:
        query = query.filter(Parcela.cliente_id == cliente_filter.id)

    # 3. Filtro por Cidade Específica
    if cidade_filter:
        # Não precisa de join extra se já fizemos join com Cliente antes
        query = query.filter(Cliente.cidade_id == cidade_filter.id)

    # 4. Filtro por Data de Vencimento
    if venc_inicio_f:
        query = query.filter(Parcela.data_vencimento >= venc_inicio_f)
    if venc_fim_f:
        query = query.filter(Parcela.data_vencimento <= venc_fim_f)

    # 5. Filtro por Data de Pagamento
    if pag_inicio_f:
        query = query.filter(Parcela.data_pagamento != None, Parcela.data_pagamento >= pag_inicio_f)
    if pag_fim_f:
        query = query.filter(Parcela.data_pagamento != None, Parcela.data_pagamento <= pag_fim_f)

    # --- Ordenação ---
    if status_filter == 'liquidada':
         query = query.order_by(Parcela.data_pagamento.desc())
    else:
         query = query.order_by(Parcela.data_vencimento.asc())

    # --- Totais (Calculados após filtros) ---
    query_sub = query.subquery()
    total_valor_parcelas = db.session.query(func.sum(query_sub.c.valor_parcela)).scalar() or 0.0
    total_valor_pago = db.session.query(func.sum(query_sub.c.valor_pago)).filter(query_sub.c.status == StatusParcela.LIQUIDADA).scalar() or 0.0
    count_parcelas = db.session.query(db.func.count()).select_from(query_sub).scalar()

    # --- Paginação ---
    parcelas_paginadas = query.paginate(page=page, per_page=15, error_out=False)

    # --- Prepara dados para o template ---
    # Não precisa mais passar lista_clientes/lista_status, o form cuida disso
    return render_template(
        'parcelas/lista_parcelas.html',
        title='Lista de Parcelas',
        form=form, # Passa o formulário para renderização
        parcelas=parcelas_paginadas,
        # Passa os filtros ATUAIS para o botão PDF e paginação
        # Ler diretamente de request.args é mais seguro aqui para manter a URL
        current_filters={
            'status': request.args.get('status', 'aberta'),
            'cliente': request.args.get('cliente', ''),
            'cidade': request.args.get('cidade', ''), # Adiciona cidade
            'venc_inicio': request.args.get('venc_inicio', ''),
            'venc_fim': request.args.get('venc_fim', ''),
            'pag_inicio': request.args.get('pag_inicio', ''),
            'pag_fim': request.args.get('pag_fim', '')
        },
        totais={
             'valor_parcelas': total_valor_parcelas,
             'valor_pago': total_valor_pago,
             'quantidade': count_parcelas
        },
        StatusParcela=StatusParcela
    )
# --- FIM DA ROTA LISTAR PARCELAS ---

# --- ROTA PARA GERAR PDF DA LISTA DE PARCELAS FILTRADA ---
@bp.route('/parcelas/pdf')
@login_required # <-- Proteger Dashboard
def listar_parcelas_pdf():
    # --- Leitura dos Filtros (da URL GET) ---
    status_filter = request.args.get('status', 'aberta')
    cliente_id_filter = request.args.get('cliente', type=int) # Pega ID como int
    cidade_id_filter = request.args.get('cidade', type=int)   # Pega ID como int
    venc_inicio_str = request.args.get('venc_inicio', '')
    venc_fim_str = request.args.get('venc_fim', '')
    pag_inicio_str = request.args.get('pag_inicio', '')
    pag_fim_str = request.args.get('pag_fim', '')

    venc_inicio_f = None
    venc_fim_f = None
    pag_inicio_f = None
    pag_fim_f = None

    
 
    try: # Converte datas string para date objects
        if venc_inicio_str: venc_inicio_f = datetime.strptime(venc_inicio_str, '%Y-%m-%d').date()
        if venc_fim_str: venc_fim_f = datetime.strptime(venc_fim_str, '%Y-%m-%d').date()
        if pag_inicio_str: pag_inicio_f = datetime.strptime(pag_inicio_str, '%Y-%m-%d').date()
        if pag_fim_str: pag_fim_f = datetime.strptime(pag_fim_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Formato de data inválido no link PDF.', 'warning') # Pode acontecer se URL for manipulada
        # Decide como tratar: gerar PDF sem filtro de data ou retornar erro?
        # Vamos gerar sem filtro de data neste caso
        venc_inicio_f = venc_fim_f = pag_inicio_f = pag_fim_f = None


    # --- REPLICA LÓGICA DE QUERY E FILTROS (sem paginação) ---
    query = Parcela.query.options(joinedload(Parcela.cliente_ref).joinedload(Cliente.cidade_ref))
    query = query.join(Cliente, Parcela.cliente_id == Cliente.id).filter(Cliente.ativo == True)

    hoje = date.today()
    if status_filter == 'aberta':
        query = query.filter(Parcela.status == StatusParcela.ABERTA, Parcela.data_vencimento >= hoje)
    elif status_filter == 'liquidada':
        query = query.filter(Parcela.status == StatusParcela.LIQUIDADA)
    elif status_filter == 'atrasada':
        query = query.filter(Parcela.status == StatusParcela.ABERTA, Parcela.data_vencimento < hoje)
    elif status_filter == 'cancelada':
         query = query.filter(Parcela.status == StatusParcela.CANCELADA)

    if cliente_id_filter:
        query = query.filter(Parcela.cliente_id == cliente_id_filter)

    if cidade_id_filter:
        query = query.filter(Cliente.cidade_id == cidade_id_filter)

    if venc_inicio_f: query = query.filter(Parcela.data_vencimento >= venc_inicio_f)
    if venc_fim_f: query = query.filter(Parcela.data_vencimento <= venc_fim_f)
    if pag_inicio_f: query = query.filter(Parcela.data_pagamento != None, Parcela.data_pagamento >= pag_inicio_f)
    if pag_fim_f: query = query.filter(Parcela.data_pagamento != None, Parcela.data_pagamento <= pag_fim_f)

    # Ordena
    if status_filter == 'liquidada':
         query = query.order_by(Parcela.data_pagamento.desc())
    else:
         query = query.order_by(Parcela.data_vencimento.asc())

    # Busca TODOS os resultados filtrados
    parcelas_filtradas = query.all()
    # --- FIM LÓGICA DE QUERY ---

    # --- Cálculo de Totais (baseado na lista filtrada) ---
    totais = {'aberto': Decimal('0.00'), 'pago': Decimal('0.00'), 'cancelado': Decimal('0.00'), 'geral_parcela': Decimal('0.00')}
    for p in parcelas_filtradas:
        totais['geral_parcela'] += (p.valor_parcela or Decimal('0.00')) # Soma total das parcelas listadas
        if p.status == StatusParcela.LIQUIDADA:
            totais['pago'] += (p.valor_pago or Decimal('0.00'))
        elif p.status == StatusParcela.ABERTA:
            totais['aberto'] += (p.valor_parcela or Decimal('0.00'))
        elif p.status == StatusParcela.CANCELADA:
            totais['cancelado'] += (p.valor_parcela or Decimal('0.00'))
    # --- FIM Totais ---

    # Busca nomes de cliente/cidade para o cabeçalho do PDF se IDs foram passados
    nome_cliente_filtro = Cliente.query.get(cliente_id_filter).nome if cliente_id_filter else "Todos"
    cidade_obj = Cidade.query.get(cidade_id_filter) if cidade_id_filter else None
    nome_cidade_filtro = f"{cidade_obj.nome_cidade}/{cidade_obj.estado}" if cidade_obj else "Todas"


  # --- Formatação das datas para exibição no cabeçalho PDF ---
    venc_inicio_fmt = venc_inicio_f.strftime('%d/%m/%Y') if venc_inicio_f else "Início"
    venc_fim_fmt = venc_fim_f.strftime('%d/%m/%Y') if venc_fim_f else "Fim"
    pag_inicio_fmt = pag_inicio_f.strftime('%d/%m/%Y') if pag_inicio_f else "Início"
    pag_fim_fmt = pag_fim_f.strftime('%d/%m/%Y') if pag_fim_f else "Fim"
    # ----------------------------------------------------------

    # Renderiza template base do PDF
    html_string = render_template(
        'parcelas/lista_parcelas_pdf_base.html',
        title=f'Relatório de Parcelas',
        parcelas=parcelas_filtradas,
        totais=totais,
        filtros_info={ # <-- USA AS VARIÁVEIS _fmt CORRIGIDAS
            'status': status_filter.replace("_", " ").capitalize(),
            'cliente': nome_cliente_filtro,
            'cidade': nome_cidade_filtro,
            'venc_inicio': venc_inicio_fmt,  # <-- Correto
            'venc_fim': venc_fim_fmt,      # <-- Correto
            'pag_inicio': pag_inicio_fmt,   # <-- Correto
            'pag_fim': pag_fim_fmt        # <-- Correto
        },
        StatusParcela=StatusParcela,
        date=date
    )
        # Passa StatusParcela e date se necessário no template PDF
    

    # Gera PDF e resposta (como antes)
    pdf_bytes = HTML(string=html_string, base_url=request.url_root).write_pdf()
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=lista_parcelas_{date.today().strftime("%Y%m%d")}.pdf'
    return response

        # --- Recalcula totais BASEADO NAS PARCELAS FILTRADAS ---
    totais_extrato = {'aberto': Decimal('0.00'), 'pago': Decimal('0.00'), 'cancelado': Decimal('0.00')} # Reseta
    for p in parcelas_cliente: # Itera sobre as parcelas JÁ filtradas por data
            if p.status == StatusParcela.LIQUIDADA:
                totais_extrato['pago'] += (p.valor_pago or Decimal('0.00'))
            elif p.status == StatusParcela.ABERTA:
                totais_extrato['aberto'] += (p.valor_parcela or Decimal('0.00'))
            elif p.status == StatusParcela.CANCELADA:
                totais_extrato['cancelado'] += (p.valor_parcela or Decimal('0.00'))
        # --- Fim Recálculo Totais ---

    return render_template('relatorios/extrato_cliente.html',
                           title='Extrato do Cliente',
                           form=form,
                           cliente=cliente_selecionado,
                           parcelas=parcelas_cliente,
                           totais=totais_extrato,
                           # Passa as datas para o botão PDF
                           data_inicio_str=data_inicio_str,
                           data_fim_str=data_fim_str)




# --- FIM ROTAS DE RELATÓRIOS ---