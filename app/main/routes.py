# app/main/routes.py (Simplificado sem Posts)
from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, \
    jsonify, current_app
from flask_login import current_user, login_required
from app import db
from app.main.forms import EditProfileForm, EmptyForm # PostForm removido
from app.models import User # Post removido da importação
from . import bp

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    # Lógica da página inicial para um sistema de cobranças
    # Por exemplo, mostrar um dashboard, lista de clientes, etc.
    # Esta é uma substituição, já que a lógica de posts foi removida.
    # Você precisará definir o que esta página faz agora.
    # Exemplo simples:
    user_data = {"username": current_user.username, "email": current_user.email}
    return render_template('index.html', title='Dashboard', user_data=user_data) # Template precisa ser ajustado

@bp.route('/explore') # Esta rota provavelmente não faz sentido sem posts. Considere removê-la.
@login_required
def explore():
    flash('Explore feature (posts) is not currently active.')
    return redirect(url_for('main.index')) # Ou renderize um template diferente

@bp.route('/user/<username>')
@login_required
def user_profile(username): # Renomeado para clareza, já que não mostra mais posts
    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm() # Para ação de seguir/deixar de seguir, se mantida
    # A lógica de paginação de posts foi removida
    return render_template('user.html', user=user, form=form, title=user.username)

# As rotas edit_profile, follow, unfollow podem permanecer, pois não dependem diretamente do modelo Post.

# ... (edit_profile, follow, unfollow como antes) ...
@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)

@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user_to_follow = User.query.filter_by(username=username).first()
        if user_to_follow is None:
            flash(f'User {username} not found.')
            return redirect(url_for('main.index'))
        if user_to_follow == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('main.user_profile', username=username)) # Rota user_profile
        current_user.follow(user_to_follow)
        db.session.commit()
        flash(f'You are following {username}!')
        return redirect(url_for('main.user_profile', username=username)) # Rota user_profile
    else:
        return redirect(url_for('main.index'))

@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user_to_unfollow = User.query.filter_by(username=username).first()
        if user_to_unfollow is None:
            flash(f'User {username} not found.')
            return redirect(url_for('main.index'))
        if user_to_unfollow == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('main.user_profile', username=username)) # Rota user_profile
        current_user.unfollow(user_to_unfollow)
        db.session.commit()
        flash(f'You are not following {username}.')
        return redirect(url_for('main.user_profile', username=username)) # Rota user_profile
    else:
        return redirect(url_for('main.index'))