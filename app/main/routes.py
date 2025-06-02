# app/routes.py
# app/main/routes.py

import requests  # Para Evolution API
import json      # Para Evolution API
from threading import Thread
import uuid
import random
import locale
from decimal import Decimal # Para garantir que valores monetários sejam tratados corretamente

from flask import (render_template, request, flash, redirect, url_for, 
                   current_app, make_response, jsonify) # Adicionado jsonify para teste API
from flask_login import login_required, current_user # Adicionado current_user

from app import db
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_, func, extract
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from app.models import Parcela, StatusParcela, Cliente, Cidade, User # Adicionado User
from app.forms import (CidadeForm, ClienteForm, GerarParcelasForm,
                       RegistrarPagamentoForm, EditarParcelaForm, FiltroParcelasForm)
from . import bp
from weasyprint import HTML

# locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8') # Opcional: se precisar de formatação de locale específica no backend

# --- INÍCIO: Funções para Evolution API ---
# app/main/routes.py (ou seu arquivo de serviço app/whatsapp_service.py)

import requests
import json
from flask import current_app

def enviar_mensagem_whatsapp_evolution(telefone_destino, mensagem_texto):
    api_url = current_app.config.get('EVOLUTION_API_URL')
    api_key_value = current_app.config.get('EVOLUTION_API_KEY_VALUE')
    api_key_header_name = current_app.config.get('EVOLUTION_API_KEY_HEADER_NAME')

    if not api_url:
        current_app.logger.error("EVOLUTION_API_URL não configurada.")
        return False, {"error": "URL da API de WhatsApp não configurada."}

    headers = {
        "Content-Type": "application/json"
    }

    auth_method_used = "Nenhuma"
    if api_key_header_name and api_key_value:
        headers[api_key_header_name] = api_key_value # Ex: headers["apikey"] = "4296..."
        auth_method_used = f"API Key (Header: {api_key_header_name})"
    else:
        # Se você não configurar API_KEY_HEADER_NAME ou API_KEY_VALUE, ele tentará sem autenticação.
        # Para sua API, isso resultaria em 401 Unauthorized, então é crucial que estejam configurados.
        current_app.logger.error("API Key ou nome do header da API Key não configurados para Evolution API.")
        return False, {"error": "Configuração de autenticação da API de WhatsApp ausente."}


    payload = {
        "number": telefone_destino,
        "text": mensagem_texto
        }

    try:
        current_app.logger.info(f"Tentando enviar WhatsApp (Evolution API) para {telefone_destino} na URL: {api_url} usando autenticação: {auth_method_used}")
        current_app.logger.debug(f"Payload: {json.dumps(payload)}")
        current_app.logger.debug(f"Headers: {headers}")

        response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=30)
        
        current_app.logger.info(f"Evolution API response status: {response.status_code}")
        current_app.logger.info(f"Evolution API response text: {response.text}")

        # Não precisa de response.raise_for_status() aqui se vamos checar o status code abaixo
        # e retornar os detalhes do erro. Se quiser que ele sempre lance exceção para 4xx/5xx, pode manter.

        response_data = {} # Inicializa com um dict vazio
        try:
            response_data = response.json()
            current_app.logger.info(f"Evolution API response JSON para {telefone_destino}: {response_data}")
        except json.JSONDecodeError:
            current_app.logger.warning(f"Resposta da Evolution API para {telefone_destino} não foi JSON válido: {response.text}")
            if response.status_code < 300: # Se o status for sucesso mas o corpo não for JSON
                return True, {"raw_response": response.text, "status_code": response.status_code}

        if response.status_code in [200, 201]: # Sucesso
            return True, response_data
        else: # Erro retornado pela API (ex: 400, 401, 403, 500)
            current_app.logger.error(f"Erro da Evolution API ao enviar para {telefone_destino} (Status: {response.status_code}): {response_data.get('error', response.text)}")
            return False, response_data
            
    except requests.exceptions.HTTPError as http_err: # Capturado por raise_for_status, ou se você o remover, não será pego aqui.
        error_details = http_err.response.text if http_err.response else 'N/A'
        current_app.logger.error(f"HTTP error ao enviar via Evolution API para {telefone_destino} (Auth: {auth_method_used}): {http_err} - Resposta: {error_details}")
        return False, {"error": f"HTTP Error: {http_err.response.status_code if http_err.response else 'N/A'}", "details": error_details}
    except requests.exceptions.ConnectionError as conn_err:
        current_app.logger.error(f"Connection error ao conectar na Evolution API ({api_url}): {conn_err}")
        return False, {"error": f"Não foi possível conectar à API de WhatsApp: {str(conn_err)}"}
    except requests.exceptions.RequestException as req_err:
        current_app.logger.error(f"Request error ao enviar via Evolution API para {telefone_destino} (Auth: {auth_method_used}): {req_err}")
        return False, {"error": str(req_err)}
    except Exception as e_gen:
        current_app.logger.error(f"Erro inesperado ao enviar via Evolution API para {telefone_destino} (Auth: {auth_method_used}): {e_gen}")
        return False, {"error": str(e_gen)}
    
def enviar_whatsapp_evolution_em_background(app_context, telefone, mensagem):
    with app_context.app_context(): 
        sucesso, detalhes_api = enviar_mensagem_whatsapp_evolution(telefone, mensagem)
        if sucesso:
            id_mensagem_enviada = "N/A"
            if isinstance(detalhes_api, dict) and 'key' in detalhes_api and isinstance(detalhes_api['key'], dict):
                id_mensagem_enviada = detalhes_api['key'].get('id', 'N/A')
            
            app_context.logger.info(f"THREAD: Mensagem para {telefone} enviada/enfileirada via Evolution API. ID da Mensagem: {id_mensagem_enviada}")
        else:
            app_context.logger.error(f"THREAD: Falha ao enviar mensagem para {telefone} via Evolution API. Detalhes: {detalhes_api}")
# --- FIM: Funções para Evolution API ---

# --- FUNÇÃO HELPER PARA AGRUPAR PARCELAS ---
def agrupar_parcelas_abertas_por_cliente(lista_de_parcelas_filtradas):
    clientes_com_parcelas_abertas = {}
    for parcela in lista_de_parcelas_filtradas:
        if parcela.status == StatusParcela.ABERTA: # Apenas parcelas ABERTAS (podem estar vencidas ou a vencer)
            cliente = parcela.cliente_ref
            if cliente not in clientes_com_parcelas_abertas:
                clientes_com_parcelas_abertas[cliente] = {'parcelas': [], 'total_devido': Decimal('0.00')}
            clientes_com_parcelas_abertas[cliente]['parcelas'].append(parcela)
            clientes_com_parcelas_abertas[cliente]['total_devido'] += parcela.valor_parcela
    return clientes_com_parcelas_abertas
# --- FIM FUNÇÃO HELPER ---

# --- FUNÇÃO HELPER PARA CONSTRUIR QUERY DE FILTRO ---
def _construir_query_parcelas_filtradas(filtros_dict):
    status_filter = filtros_dict.get('status', 'aberta')
    
    cliente_id_str = filtros_dict.get('cliente_id') or filtros_dict.get('cliente') # Tenta 'cliente_id' ou 'cliente'
    cliente_id_filter = None
    if cliente_id_str and cliente_id_str != '' and cliente_id_str != '__None':
        try:
            cliente_id_filter = int(cliente_id_str)
        except ValueError:
            current_app.logger.warning(f"Valor inválido para cliente_id no filtro: {cliente_id_str}")

    cidade_id_str = filtros_dict.get('cidade_id') or filtros_dict.get('cidade')
    cidade_id_filter = None
    if cidade_id_str and cidade_id_str != '' and cidade_id_str != '__None':
        try:
            cidade_id_filter = int(cidade_id_str)
        except ValueError:
            current_app.logger.warning(f"Valor inválido para cidade_id no filtro: {cidade_id_str}")

    venc_inicio_str = filtros_dict.get('venc_inicio', '')
    venc_fim_str = filtros_dict.get('venc_fim', '')
    pag_inicio_str = filtros_dict.get('pag_inicio', '')
    pag_fim_str = filtros_dict.get('pag_fim', '')

    venc_inicio_f, venc_fim_f, pag_inicio_f, pag_fim_f = None, None, None, None
    try:
        if venc_inicio_str: venc_inicio_f = datetime.strptime(venc_inicio_str, '%Y-%m-%d').date()
        if venc_fim_str: venc_fim_f = datetime.strptime(venc_fim_str, '%Y-%m-%d').date()
        if pag_inicio_str: pag_inicio_f = datetime.strptime(pag_inicio_str, '%Y-%m-%d').date()
        if pag_fim_str: pag_fim_f = datetime.strptime(pag_fim_str, '%Y-%m-%d').date()
    except ValueError:
        current_app.logger.warning("Formato de data inválido recebido nos filtros da query.")
        # Não define as datas se o formato for inválido, efetivamente ignorando o filtro de data
        pass 

    query = Parcela.query.options(joinedload(Parcela.cliente_ref).joinedload(Cliente.cidade_ref))
    query = query.join(Cliente, Parcela.cliente_id == Cliente.id).filter(Cliente.ativo == True)
    hoje = date.today()

    if status_filter == 'aberta':
        query = query.filter(Parcela.status == StatusParcela.ABERTA, Parcela.data_vencimento >= hoje)
    elif status_filter == 'atrasada':
        query = query.filter(Parcela.status == StatusParcela.ABERTA, Parcela.data_vencimento < hoje)
    elif status_filter == 'liquidada':
        query = query.filter(Parcela.status == StatusParcela.LIQUIDADA)
    elif status_filter == 'cancelada':
        query = query.filter(Parcela.status == StatusParcela.CANCELADA)
    
    if cliente_id_filter: query = query.filter(Parcela.cliente_id == cliente_id_filter)
    if cidade_id_filter: query = query.filter(Cliente.cidade_id == cidade_id_filter)
    if venc_inicio_f: query = query.filter(Parcela.data_vencimento >= venc_inicio_f)
    if venc_fim_f: query = query.filter(Parcela.data_vencimento <= venc_fim_f)
    if pag_inicio_f: query = query.filter(Parcela.data_pagamento != None, Parcela.data_pagamento >= pag_inicio_f)
    if pag_fim_f: query = query.filter(Parcela.data_pagamento != None, Parcela.data_pagamento <= pag_fim_f)
    
    return query, status_filter
# --- FIM FUNÇÃO HELPER QUERY ---

# --- ROTAS PRINCIPAIS ---
@bp.route('/')
@bp.route('/index')
@bp.route('/dashboard')
@login_required
def dashboard():
    hoje = date.today()
    ano_atual = hoje.year
    mes_atual_num = hoje.month
    
    meses_pt = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    nome_mes_atual = meses_pt.get(mes_atual_num, str(mes_atual_num))
    mes_ano_formatado = f"{nome_mes_atual}/{ano_atual}"

    a_receber_mes_atual = db.session.query(func.sum(Parcela.valor_parcela)).join(Cliente, Parcela.cliente_id == Cliente.id).filter(Cliente.ativo == True, Parcela.status == StatusParcela.ABERTA, extract('year', Parcela.data_vencimento) == ano_atual, extract('month', Parcela.data_vencimento) == mes_atual_num).scalar() or Decimal('0.0')
    
    # Ajuste para 'recebido_30_dias' - se refere a parcelas PAGAS no mês atual
    # Ou se refere a parcelas com data de PAGAMENTO nos últimos 30 dias? Vou assumir PAGAS NO MÊS ATUAL.
    # Se for últimos 30 dias a partir de hoje, a lógica de data é diferente.
    recebido_mes_atual = db.session.query(func.sum(Parcela.valor_pago)).join(Cliente, Parcela.cliente_id == Cliente.id).filter(Cliente.ativo == True, Parcela.status == StatusParcela.LIQUIDADA, extract('year', Parcela.data_pagamento) == ano_atual, extract('month', Parcela.data_pagamento) == mes_atual_num).scalar() or Decimal('0.0')

    total_atrasado = db.session.query(func.sum(Parcela.valor_parcela)).join(Cliente, Parcela.cliente_id == Cliente.id).filter(Cliente.ativo == True, Parcela.status == StatusParcela.ABERTA, Parcela.data_vencimento < hoje).scalar() or Decimal('0.0')
    
    labels_chart, data_recebido_chart, data_a_vencer_chart = [], [], []
    for i in range(5, -1, -1):
        mes_referencia = hoje - relativedelta(months=i)
        labels_chart.append(mes_referencia.strftime("%m/%Y"))
        ano_ref, mes_ref = mes_referencia.year, mes_referencia.month
        
        q_base_chart = Parcela.query.join(Cliente, Parcela.cliente_id == Cliente.id).filter(Cliente.ativo == True)
        
        a_vencer_mes = db.session.query(func.sum(Parcela.valor_parcela)).select_from(q_base_chart).filter(Parcela.status == StatusParcela.ABERTA, extract('year', Parcela.data_vencimento) == ano_ref, extract('month', Parcela.data_vencimento) == mes_ref).scalar() or 0.0
        data_a_vencer_chart.append(float(a_vencer_mes))
        
        recebido_mes_grafico = db.session.query(func.sum(Parcela.valor_pago)).select_from(q_base_chart).filter(Parcela.status == StatusParcela.LIQUIDADA, extract('year', Parcela.data_pagamento) == ano_ref, extract('month', Parcela.data_pagamento) == mes_ref).scalar() or 0.0
        data_recebido_chart.append(float(recebido_mes_grafico))

    chart_data = {
        'labels': labels_chart,
        'datasets': [
             {'label': 'Valor Recebido', 'backgroundColor': 'rgba(75, 192, 192, 0.5)', 'borderColor': 'rgb(75, 192, 192)', 'data': data_recebido_chart, 'borderWidth': 1},
             {'label': 'Valor a Vencer', 'backgroundColor': 'rgba(255, 159, 64, 0.5)', 'borderColor': 'rgb(255, 159, 64)', 'data': data_a_vencer_chart, 'borderWidth': 1}
        ]
    }
    return render_template('dashboard/index.html', title='e-Cobranças - Dashboard', mes_ano_atual=hoje.strftime("%m/%Y"), a_receber_mes_atual=a_receber_mes_atual, recebido_30_dias=recebido_mes_atual, total_atrasado=total_atrasado, nome_mes_atual=mes_ano_formatado, chart_data=chart_data)

# --- ROTAS DE CIDADES ---
@bp.route('/cidades')
@bp.route('/cidades/lista')
@login_required
def listar_cidades():
    page = request.args.get('page', 1, type=int)
    cidades = Cidade.query.order_by(Cidade.nome_cidade).paginate(page=page, per_page=10, error_out=False)
    return render_template('cidades/lista_cidades.html', cidades=cidades, title='e-Cobranças - Lista de Cidades')

@bp.route('/cidades/novo', methods=['GET', 'POST'])
@login_required
def adicionar_cidade():
    form = CidadeForm()
    if form.validate_on_submit():
        nova_cidade = Cidade(nome_cidade=form.nome_cidade.data, estado=form.estado.data)
        db.session.add(nova_cidade)
        try:
            db.session.commit()
            flash(f'Cidade "{nova_cidade.nome_cidade}/{nova_cidade.estado}" adicionada com sucesso!', 'success')
            return redirect(url_for('main.listar_cidades'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar cidade: {str(e)}', 'danger')
    return render_template('cidades/form_cidade.html', form=form, title='e-Cobranças - Adicionar Cidade', legend='Nova Cidade')

@bp.route('/cidades/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cidade(id):
    cidade = db.get_or_404(Cidade, id)
    form = CidadeForm(obj=cidade)
    if form.validate_on_submit():
        cidade.nome_cidade = form.nome_cidade.data
        cidade.estado = form.estado.data
        try:
            db.session.commit()
            flash(f'Cidade "{cidade.nome_cidade}/{cidade.estado}" atualizada com sucesso!', 'success')
            return redirect(url_for('main.listar_cidades'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar cidade: {str(e)}', 'danger')
    return render_template('cidades/form_cidade.html', form=form, title='e-Cobranças - Editar Cidade', legend=f'Editando: {cidade.nome_cidade}')

@bp.route('/cidades/<int:id>/deletar', methods=['POST'])
@login_required
def deletar_cidade(id):
    cidade = db.get_or_404(Cidade, id)
    if cidade.clientes.first():
         flash(f'Não é possível excluir a cidade "{cidade.nome_cidade}/{cidade.estado}" pois existem clientes cadastrados nela.', 'warning')
         return redirect(url_for('main.listar_cidades'))
    try:
        nome_cidade_deletada = f"{cidade.nome_cidade}/{cidade.estado}"
        db.session.delete(cidade)
        db.session.commit()
        flash(f'Cidade "{nome_cidade_deletada}" excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir cidade: {str(e)}', 'danger')
    return redirect(url_for('main.listar_cidades'))

# --- ROTAS DE CLIENTES ---
@bp.route('/clientes')
@login_required
def listar_clientes():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    status_filter = request.args.get('status', 'ativos')
    query = Cliente.query.options(joinedload(Cliente.cidade_ref))
    if status_filter == 'ativos': query = query.filter(Cliente.ativo == True)
    elif status_filter == 'inativos': query = query.filter(Cliente.ativo == False)
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(or_(Cliente.nome.ilike(search_term), Cliente.contato.ilike(search_term)))
    clientes = query.order_by(Cliente.nome).paginate(page=page, per_page=10, error_out=False)
    return render_template('clientes/lista_clientes.html', clientes=clientes, title='e-Cobranças - Lista de Clientes', search_query=search_query, status_filter=status_filter)

@bp.route('/clientes/novo', methods=['GET', 'POST'])
@login_required
def adicionar_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        novo_cliente = Cliente(
            nome=form.nome.data, contato=form.contato.data, conexao=form.conexao.data,
            endereco=form.endereco.data, cidade_id=form.cidade.data.id, telefone=form.telefone.data,
            email=form.email.data, valor_mensalidade=form.valor_mensalidade.data,
            dia_cobranca=form.dia_cobranca.data, obs=form.obs.data, ativo=form.ativo.data
        )
        db.session.add(novo_cliente)
        try:
            db.session.commit()
            flash(f'Cliente "{novo_cliente.nome}" adicionado com sucesso!', 'success')
            return redirect(url_for('main.listar_clientes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar cliente: {str(e)}', 'danger')
    return render_template('clientes/form_cliente.html', form=form, title='e-Cobranças - Adicionar Cliente', legend='Novo Cliente')

@bp.route('/clientes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    cliente = db.get_or_404(Cliente, id)
    form = ClienteForm(obj=cliente)
    if request.method == 'GET':
         form.cidade.data = cliente.cidade_ref
    if form.validate_on_submit():
        form.populate_obj(cliente) # Popula o objeto cliente com dados do form
        cliente.cidade_id = form.cidade.data.id # Atribuição manual para QuerySelectField
        try:
            db.session.commit()
            flash(f'Cliente "{cliente.nome}" atualizado com sucesso!', 'success')
            return redirect(url_for('main.listar_clientes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar cliente: {str(e)}', 'danger')
    return render_template('clientes/form_cliente.html', form=form, title='e-Cobranças - Editar Cliente', legend=f'Editando: {cliente.nome}')

@bp.route('/clientes/<int:id>/desativar', methods=['POST'])
@login_required
def desativar_cliente(id):
    cliente = db.get_or_404(Cliente, id)
    try:
        nome_cliente_desativado = cliente.nome
        cliente.ativo = False
        db.session.commit()
        flash(f'Cliente "{nome_cliente_desativado}" desativado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao desativar cliente: {str(e)}', 'danger')
    return redirect(url_for('main.listar_clientes'))

# --- ROTAS DE COBRANÇAS/PARCELAS ---
@bp.route('/cobrancas/gerar', methods=['GET', 'POST'])
@login_required
def gerar_parcelas():
    form = GerarParcelasForm()
    if form.validate_on_submit():
        cliente_selecionado = form.cliente.data
        valor = form.valor_parcela.data
        quantidade = form.quantidade_parcelas.data
        primeira_data = form.primeiro_vencimento.data
        periodicidade = form.periodicidade.data
        data_geracao = datetime.utcnow()
        cobranca_id_unico = str(uuid.uuid4())
        random_part = random.randint(100000, 999999)
        try:
            for i in range(quantidade):
                numero_sequencial = i + 1
                data_vencimento_parcela = primeira_data
                if i > 0 and periodicidade == 'mensal':
                    data_vencimento_parcela = primeira_data + relativedelta(months=i)
                numero_parcela_formatado = f"{random_part}-{numero_sequencial}/{quantidade}"
                nova_parcela = Parcela(
                    cobranca_uuid=cobranca_id_unico, cliente_id=cliente_selecionado.id,
                    numero_parcela=numero_parcela_formatado, total_parcelas=quantidade,
                    valor_parcela=valor, data_geracao=data_geracao,
                    data_vencimento=data_vencimento_parcela, status=StatusParcela.ABERTA
                )
                db.session.add(nova_parcela)
            db.session.commit()
            flash(f'{quantidade} parcelas geradas com sucesso para o cliente {cliente_selecionado.nome}!', 'success')
            return redirect(url_for('main.listar_parcelas')) # Alterado para listar_parcelas
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao gerar parcelas: {str(e)}', 'danger')
    return render_template('cobrancas/gerar_parcelas.html', form=form, title='e-Cobranças - Gerar Parcelas')

@bp.route('/parcelas/<int:id>/pagar', methods=['POST'])
@login_required
def registrar_pagamento(id):
    parcela = db.get_or_404(Parcela, id)
    if parcela.status != StatusParcela.ABERTA:
        flash('Esta parcela não está aberta para pagamento.', 'warning')
        return redirect(request.referrer or url_for('main.listar_parcelas'))
    
    # Usar request.form para pegar dados de um formulário HTML simples
    try:
        data_pagamento_str = request.form.get('data_pagamento')
        valor_pago_str = request.form.get('valor_pago')

        if not data_pagamento_str or not valor_pago_str:
            flash('Data do pagamento e valor pago são obrigatórios.', 'danger')
            return redirect(request.referrer or url_for('main.listar_parcelas'))

        parcela.data_pagamento = datetime.strptime(data_pagamento_str, '%Y-%m-%d').date()
        parcela.valor_pago = Decimal(valor_pago_str.replace(',', '.')) # Trata vírgula e ponto
        parcela.status = StatusParcela.LIQUIDADA
        db.session.commit()
        flash(f'Pagamento da parcela {parcela.numero_parcela} registrado com sucesso!', 'success')
    except ValueError:
        flash('Formato inválido para data ou valor.', 'danger')
        db.session.rollback()
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar pagamento: {str(e)}', 'danger')
    return redirect(request.referrer or url_for('main.listar_parcelas'))


@bp.route('/parcelas/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar_parcela(id):
    parcela = db.get_or_404(Parcela, id)
    if parcela.status != StatusParcela.ABERTA:
        flash('Apenas parcelas abertas podem ser canceladas.', 'warning')
        return redirect(request.referrer or url_for('main.listar_parcelas'))
    try:
        parcela.status = StatusParcela.CANCELADA
        db.session.commit()
        flash(f'Parcela {parcela.numero_parcela} cancelada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao cancelar parcela: {str(e)}', 'danger')
    return redirect(request.referrer or url_for('main.listar_parcelas'))

@bp.route('/parcelas/<int:id>/desfazer_liquidacao', methods=['POST'])
@login_required
def desfazer_liquidacao_parcela(id):
    parcela = db.get_or_404(Parcela, id)
    if parcela.status != StatusParcela.LIQUIDADA:
        flash('Apenas parcelas liquidadas podem ter a liquidação desfeita.', 'warning')
        return redirect(request.referrer or url_for('main.listar_parcelas'))
    try:
        parcela.status = StatusParcela.ABERTA
        parcela.data_pagamento = None
        parcela.valor_pago = None
        db.session.commit()
        flash(f'Liquidação da parcela {parcela.numero_parcela} desfeita! Status: Aberta.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao desfazer liquidação: {str(e)}', 'danger')
    return redirect(request.referrer or url_for('main.listar_parcelas'))

@bp.route('/parcelas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_parcela(id):
    parcela = db.get_or_404(Parcela, id)
    if parcela.status != StatusParcela.ABERTA:
        flash('Apenas parcelas abertas podem ser editadas.', 'warning')
        return redirect(url_for('main.listar_parcelas'))
    form = EditarParcelaForm(obj=parcela)
    if form.validate_on_submit():
        try:
            parcela.valor_parcela = form.valor_parcela.data
            parcela.data_vencimento = form.data_vencimento.data
            db.session.commit()
            flash(f'Parcela {parcela.numero_parcela} atualizada com sucesso!', 'success')
            return redirect(url_for('main.listar_parcelas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar parcela: {str(e)}', 'danger')
    return render_template('cobrancas/form_editar_parcela.html', title='e-Cobranças - Editar Parcela', form=form, parcela=parcela)


@bp.route('/parcelas')
@bp.route('/parcelas/lista')
@login_required
def listar_parcelas():
    page = request.args.get('page', 1, type=int)
    form = FiltroParcelasForm(request.args)
    query, status_filter_usado = _construir_query_parcelas_filtradas(request.args)

    if status_filter_usado == 'liquidada':
         query = query.order_by(Parcela.data_pagamento.desc(), Parcela.data_vencimento.desc())
    else:
         query = query.order_by(Parcela.data_vencimento.asc())

    query_sub = query.subquery()
    total_valor_parcelas = db.session.query(func.sum(query_sub.c.valor_parcela)).scalar() or Decimal('0.00')
    # Corrigido para usar query_sub para total_valor_pago também
    total_valor_pago = db.session.query(func.sum(query_sub.c.valor_pago)).filter(query_sub.c.status == StatusParcela.LIQUIDADA).scalar() or Decimal('0.00')
    count_parcelas = db.session.query(db.func.count(query_sub.c.id)).scalar() or 0


    parcelas_paginadas = query.paginate(page=page, per_page=15, error_out=False)
    
    current_filters_for_template = {k: v for k, v in request.args.items() if v} # Pega apenas filtros com valor
    current_filters_for_template.setdefault('status', 'aberta') # Garante default para status

    return render_template(
        'parcelas/lista_parcelas.html', title='e-Cobranças - Lista de Parcelas',
        form=form, parcelas=parcelas_paginadas,
        current_filters=current_filters_for_template,
        totais={'valor_parcelas': total_valor_parcelas, 'valor_pago': total_valor_pago, 'quantidade': count_parcelas},
        StatusParcela=StatusParcela, date=date
    )

@bp.route('/parcelas/pdf')
@login_required
def listar_parcelas_pdf():
    query, status_filter_usado = _construir_query_parcelas_filtradas(request.args)
    if status_filter_usado == 'liquidada':
         query = query.order_by(Parcela.data_pagamento.desc())
    else:
         query = query.order_by(Parcela.data_vencimento.asc())
    parcelas_filtradas = query.all()

    totais_pdf = {'aberto': Decimal('0.00'), 'pago': Decimal('0.00'), 'cancelado': Decimal('0.00'), 'geral_parcela': Decimal('0.00')}
    for p_pdf in parcelas_filtradas:
        totais_pdf['geral_parcela'] += (p_pdf.valor_parcela or Decimal('0.00'))
        if p_pdf.status == StatusParcela.LIQUIDADA: totais_pdf['pago'] += (p_pdf.valor_pago or Decimal('0.00'))
        elif p_pdf.status == StatusParcela.ABERTA: totais_pdf['aberto'] += (p_pdf.valor_parcela or Decimal('0.00'))
        elif p_pdf.status == StatusParcela.CANCELADA: totais_pdf['cancelado'] += (p_pdf.valor_parcela or Decimal('0.00'))

    cliente_id_filter = request.args.get('cliente', type=int)
    cidade_id_filter = request.args.get('cidade', type=int)
    nome_cliente_filtro = Cliente.query.get(cliente_id_filter).nome if cliente_id_filter else "Todos"
    cidade_obj = Cidade.query.get(cidade_id_filter) if cidade_id_filter else None
    nome_cidade_filtro = f"{cidade_obj.nome_cidade}/{cidade_obj.estado}" if cidade_obj else "Todas"
    
    def format_date_for_pdf(date_str):
        if not date_str: return "N/A"
        try: return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError: return date_str # Retorna original se não puder formatar

    filtros_info_pdf = {
        'status': status_filter_usado.replace("_", " ").capitalize(),
        'cliente': nome_cliente_filtro, 'cidade': nome_cidade_filtro,
        'venc_inicio': format_date_for_pdf(request.args.get('venc_inicio')),
        'venc_fim': format_date_for_pdf(request.args.get('venc_fim')),
        'pag_inicio': format_date_for_pdf(request.args.get('pag_inicio')),
        'pag_fim': format_date_for_pdf(request.args.get('pag_fim'))
    }

    html_string = render_template(
        'parcelas/lista_parcelas_pdf_base.html', title=f'e-Cobranças - Relatório de Parcelas',
        parcelas=parcelas_filtradas, totais=totais_pdf, filtros_info=filtros_info_pdf,
        StatusParcela=StatusParcela, date=date
    )
    pdf_bytes = HTML(string=html_string, base_url=request.url_root).write_pdf()
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=lista_parcelas_{date.today().strftime("%Y%m%d")}.pdf'
    return response

# --- ROTA PARA ENVIAR LEMBRETES WHATSAPP EM LOTE ---
@bp.route('/parcelas/enviar_lembretes_whatsapp_lote', methods=['POST'])
@login_required
def enviar_lembretes_whatsapp_lote():
    query_base, _ = _construir_query_parcelas_filtradas(request.form)
    parcelas_filtradas_para_lembrete = query_base.filter(
        Parcela.status == StatusParcela.ABERTA # Somente parcelas ABERTAS (inclui atrasadas e a vencer)
    ).order_by(Parcela.cliente_id, Parcela.data_vencimento).all()

    if not parcelas_filtradas_para_lembrete:
        flash('Nenhuma parcela aberta ou atrasada encontrada com os filtros aplicados para enviar lembretes.', 'info')
        return redirect(url_for('main.listar_parcelas', **request.form.to_dict(flat=True)))

    clientes_a_notificar = agrupar_parcelas_abertas_por_cliente(parcelas_filtradas_para_lembrete)

    if not clientes_a_notificar:
        flash('Nenhum cliente com parcelas abertas/atrasadas encontrado nos filtros para notificar.', 'info')
        return redirect(url_for('main.listar_parcelas', **request.form.to_dict(flat=True)))

    app_context_obj = current_app._get_current_object() # Correção aqui
    mensagens_programadas_count = 0
    clientes_problema_count = 0

    for cliente, dados in clientes_a_notificar.items():
        if not cliente.telefone:
            clientes_problema_count += 1
            current_app.logger.warning(f"Cliente {cliente.nome} (ID: {cliente.id}) não tem telefone para envio de lembrete.")
            continue

        telefone_formatado = ''.join(filter(str.isdigit, cliente.telefone))
        if len(telefone_formatado) > 2 and telefone_formatado.startswith('55'):
             pass # Já tem DDI Brasil
        elif len(telefone_formatado) >= 10: # DDD + Número
            telefone_formatado = "55" + telefone_formatado
        else:
            clientes_problema_count += 1
            current_app.logger.warning(f"Telefone de {cliente.nome} (ID: {cliente.id}) inválido para API Evolution: {cliente.telefone}. Formato esperado: 55DDDXXXXXXXXX")
            continue
        
        mensagem_partes = [f"Olá {cliente.nome}! Lembrete e-Cobranças:"]
        mensagem_partes.append("Constam as seguintes parcelas em aberto/atraso em seu nome:")
        for p in dados['parcelas']:
            estado_parcela_txt = "com vencimento em" if not p.esta_vencida else "vencida em"
            mensagem_partes.append(
                f"- Parcela nº {p.numero_parcela}, {estado_parcela_txt} {p.data_vencimento.strftime('%d/%m/%Y')}, Valor: R$ {p.valor_parcela:.2f}"
            )
        mensagem_partes.append(f"\nValor total pendente (desta seleção): R$ {dados['total_devido']:.2f}")
        mensagem_partes.append("\nPara regularizar ou mais detalhes, entre em contato ou acesse nosso portal.")
        mensagem_final = "\n".join(mensagem_partes)

        thread = Thread(target=enviar_whatsapp_evolution_em_background, 
                        args=(app_context_obj, telefone_formatado, mensagem_final)) # Correção aqui
        thread.start()
        mensagens_programadas_count += 1

    feedback_message = f"Processo de envio de lembretes WhatsApp (API Evolution) iniciado para {mensagens_programadas_count} cliente(s)."
    if clientes_problema_count > 0:
        feedback_message += f" {clientes_problema_count} cliente(s) não puderam ser processados por falta de telefone ou formato inválido."
    
    flash(feedback_message, 'info')
    return redirect(url_for('main.listar_parcelas', **request.form.to_dict(flat=True)))
# --- FIM ROTAS DE COBRANÇAS/PARCELAS ---

# Rota de teste para API Evolution (opcional, para debug)
@bp.route('/teste_whatsapp_api_evolution', methods=['GET'])
@login_required
def teste_whatsapp_api_evolution():
    if not getattr(current_user, 'is_admin', False): # Verifica se o usuário é admin
        flash('Acesso negado a esta funcionalidade.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Substitua pelo seu número de teste no formato da API (ex: 5511999998888)
    num_teste = "5599991266682" # COLOQUE SEU NÚMERO DE TESTE REAL AQUI
    msg_teste = "Olá! Teste da API Evolution para e-Cobranças. Sucesso! 🎉"
    
    if num_teste == "55SEUDDDSEUNUMERO": # Lembrete para não commitar número real
        flash("Por favor, defina um número de telefone real para o teste.", "warning")
        return "Configure um número de teste na rota.", 400

    sucesso, detalhes = enviar_mensagem_whatsapp_evolution(num_teste, msg_teste)
    
    if sucesso:
        flash(f"Teste de WhatsApp enviado para {num_teste}. Resposta da API: {detalhes}", "success")
    else:
        flash(f"Falha no teste de WhatsApp para {num_teste}. Resposta da API: {detalhes}", "danger")
    
    return redirect(url_for('main.dashboard'))