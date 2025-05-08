# app/auth/routes.py
from flask import render_template, redirect, url_for, flash, request,current_app
from urllib.parse import urlparse as urllib_urlparse 
from flask_login import login_user, logout_user, current_user
# REMOVIDO: from flask_babel import _
from app import db
from . import bp # app.auth.bp
from .forms import (LoginForm, RegistrationForm,
                    ResetPasswordRequestForm, ResetPasswordForm) # app.auth.forms
from app.models import User
#from .email import send_password_reset_email # app.auth.email

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuario ou Senha inválidos')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urllib_urlparse(next_page).netloc != '':
            next_page = url_for('main.dashboard') # Ou sua rota principal
        return redirect(next_page)

    return render_template('auth/login.html', title='Fazer login', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    flash('Logout realizado com sucesso!')
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Parabéns, você está registrado!')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Registrar-se', form=form)

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
           # send_password_reset_email(user)
            flash('senha de redefinição enviada para o seu email. desabilitada por enquanto')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title='Reset Password', form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form, title='Reset Your Password')