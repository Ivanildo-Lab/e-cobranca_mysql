# app/auth/__init__.py
from flask import Blueprint

# Cria o blueprint chamado 'auth'
# Este 'bp' será importado pelo app/__init__.py principal para registro
bp = Blueprint('auth', __name__)

# Importa as rotas e formulários pertencentes a ESTE blueprint (auth)
# Essas importações são feitas no final para evitar ciclos
from app.auth import routes, forms
# app/auth/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import db
from app.auth import bp # Importa o blueprint 'auth'
from app.auth.forms import LoginForm, RegistrationForm # Importa os formulários de auth
from app.models import User # Importa o modelo User

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Se o usuário já está logado, redireciona para o dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard')) # Redireciona para o BP 'main', rota 'dashboard'

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.username == form.username.data))
        # user = User.query.filter_by(username=form.username.data).first() # Alternativa < 2.0

        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos.', 'danger')
            return redirect(url_for('auth.login')) # Redireciona para a própria rota de login

        # Se usuário e senha são válidos, faz o login
        login_user(user, remember=form.remember_me.data)
        flash(f'Login bem-sucedido! Bem-vindo, {user.username}.', 'success')

        # Redireciona para a página que o usuário tentava acessar (next) ou para o dashboard
        next_page = request.args.get('next')
        # Segurança: verifica se next_page é relativo (não um site externo)
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.dashboard') # Rota principal após login
        return redirect(next_page)

    return render_template('auth/login.html', title='Login', form=form)

@bp.route('/logout')
@login_required # Só pode deslogar quem está logado
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('auth.login')) # Redireciona para a página de login

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
            flash('Parabéns, você foi registrado com sucesso! Faça o login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar: {e}', 'danger') # Ou uma mensagem genérica
            # Logar o erro 'e' seria importante aqui

    return render_template('auth/register.html', title='Registrar', form=form)