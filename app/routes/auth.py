from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app import db
from app.models import User
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if user.status == 'banned':
                flash('Tu cuenta ha sido baneada.')
                return redirect(url_for('auth.login'))
            
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('main.index'))
        else:
            flash('Usuario o contraseña incorrectos.')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.')
        elif len(password) < 4:
            flash('La contraseña debe tener al menos 4 caracteres.')
        else:
            new_user = User(
                username=username, 
                password_hash=generate_password_hash(password),
                role='user'
            )
            db.session.add(new_user)
            db.session.commit()
            
            # Auto login after register
            session['user_id'] = new_user.id
            session['username'] = new_user.username
            session['role'] = new_user.role
            
            return redirect(url_for('main.index'))
            
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
