from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from app import db
from app.models import User

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

@profile_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not user.check_password(current_password):
            flash('La contraseña actual es incorrecta.', 'error')
        elif new_password != confirm_password:
            flash('Las nuevas contraseñas no coinciden.', 'error')
        elif len(new_password) < 4:
            flash('La nueva contraseña debe tener al menos 4 caracteres.', 'error')
        else:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('Contraseña actualizada con éxito.')
            return redirect(url_for('main.index'))

    return render_template('profile/change_password.html')
