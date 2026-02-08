from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import psutil
from app import db
from app.models import Note, Task

tools_bp = Blueprint('tools', __name__)

@tools_bp.before_request
def login_required():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

@tools_bp.route('/monitor')
def monitor():
    # Obtener métricas del sistema
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return render_template(
        'tools/monitor.html', 
        cpu=cpu, 
        ram=ram, 
        disk=disk
    )

@tools_bp.route('/notes', methods=['GET', 'POST'])
def notes():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        is_public = True if request.form.get('is_public') else False
        
        new_note = Note(
            title=title, 
            content=content, 
            is_public=is_public, 
            user_id=session['user_id']
        )
        db.session.add(new_note)
        db.session.commit()
        flash('Nota creada.')
        return redirect(url_for('tools.notes'))
        
    my_notes = Note.query.filter_by(user_id=session['user_id']).all()
    # Notas públicas de otros usuarios también? Dejémoslo solo privadas y propias por ahora o implementación simple.
    return render_template('tools/notes.html', notes=my_notes)

@tools_bp.route('/notes/delete/<int:note_id>')
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id == session['user_id'] or session.get('role') == 'admin':
        db.session.delete(note)
        db.session.commit()
    return redirect(url_for('tools.notes'))

@tools_bp.route('/todo', methods=['GET', 'POST'])
def todo():
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            task = Task(content=content, user_id=session['user_id'])
            db.session.add(task)
            db.session.commit()
        return redirect(url_for('tools.todo'))
        
    tasks = Task.query.filter_by(user_id=session['user_id']).order_by(Task.timestamp.desc()).all()
    return render_template('tools/todo.html', tasks=tasks)

@tools_bp.route('/todo/toggle/<int:task_id>')
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == session['user_id']:
        task.is_done = not task.is_done
        db.session.commit()
    return redirect(url_for('tools.todo'))

@tools_bp.route('/todo/delete/<int:task_id>')
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == session['user_id']:
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for('tools.todo'))
