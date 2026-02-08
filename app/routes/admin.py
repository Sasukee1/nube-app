from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from app import db
from app.models import User
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
def admin_required():
    if session.get('role') != 'admin':
        flash('Acceso denegado.')
        return redirect(url_for('main.index'))

@admin_bp.route('/')
def panel():
    from app.models import SiteConfig
    users = User.query.all()
    # No necesitamos pasar current_theme aquí porque está en context_processor,
    # pero si queremos mostrar cuál está seleccionado en un <select>, sí podría ser útil si no usamos la variable global
    # Usaremos current_theme del context processor en el template.
    return render_template('admin/panel.html', users=users)

@admin_bp.route('/set_theme', methods=['POST'])
def set_theme():
    from app.models import SiteConfig
    theme = request.form.get('theme')
    valid_themes = ['theme-dark', 'theme-light', 'theme-navidad', 'theme-colombia', 'theme-halloween', 'theme-socialista']
    
    if theme in valid_themes:
        conf = SiteConfig.query.filter_by(key='current_theme').first()
        if not conf:
            conf = SiteConfig(key='current_theme', value=theme)
            db.session.add(conf)
        else:
            conf.value = theme
        db.session.commit()
        flash('Tema actualizado.')
    else:
        flash('Tema no válido.')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/ban/<int:user_id>')
def ban_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'ADMIN':
        flash('No puedes banear al admin.')
    else:
        user.status = 'banned'
        db.session.commit()
        flash(f'Usuario {user.username} baneado.')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/unban/<int:user_id>')
def unban_user(user_id):
    user = User.query.get_or_404(user_id)
    user.status = 'active'
    db.session.commit()
    flash(f'Usuario {user.username} desbaneado.')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'ADMIN':
        flash('No puedes borrar al admin.')
    else:
        # Borrar archivos y mensajes en cascada si no está configurado en DB
        # En models definimos relationship, pero no cascade delete explícito en db.relationship
        # SQLAlchemy manejará set null o error si no se configura cascade.
        # Por simplicidad aquí lo borramos.
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuario {user.username} eliminado.')
    return redirect(url_for('admin.panel'))

@admin_bp.route('/change_role/<int:user_id>', methods=['POST'])
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'ADMIN':
        flash('No se puede cambiar rol de ADMIN.')
    else:
        new_role = request.form.get('role')
        if new_role in ['user', 'admin']:
            user.role = new_role
            db.session.commit()
            flash('Rol actualizado.')
    return redirect(url_for('admin.panel'))
