from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app # current_app añadido
import vercel_blob # Nueva importación
from werkzeug.utils import secure_filename
from app import db
from app.models import User, File, Message
from datetime import datetime
from urllib.parse import urlparse 
import yt_dlp
import requests
import os 
import tempfile
import time # Importación añadida


main_bp = Blueprint('main', __name__)

@main_bp.before_request
def check_banned_status():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.status == 'banned':
            session.clear()
            flash('Tu cuenta ha sido baneada.')
            return redirect(url_for('auth.login'))

@main_bp.route('/')
@main_bp.route('/<category_name>')
def index(category_name='all'):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # Evitar conflicto si category_name coincide con una ruta (esto es un poco frágil en el diseño original, 
    # mejor sería /files/<category>, pero mantendremos compatibilidad sutil o lo mejoramos).
    # Como definimos endpoints específicos antes, Flask suele manejarlo, pero 'all' es seguro.
    
    # Si category_name es 'favicon.ico' u otros, ignorar
    if category_name in ['favicon.ico', 'static']:
        return "", 404

    query = File.query
    if category_name != 'all':
        query = query.filter_by(category=category_name)
    
    files = query.order_by(File.upload_date.desc()).all()
    
    # Obtener todas las categorías para el filtro
    all_categories = db.session.query(File.category).distinct().all()
    all_categories = sorted([c[0] for c in all_categories])
    
    # Mensajes para el chat (limitados a los últimos 50 por ejemplo)
    messages = Message.query.order_by(Message.timestamp.asc()).limit(50).all()
    
    return render_template(
        'main/index.html',
        files=files,
        messages=messages,
        username=session['username'],
        role=session.get('role'),
        categories=all_categories,
        current_category=category_name
    )

@main_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if 'file' not in request.files or not request.files['file'].filename:
        flash('No se seleccionó ningún archivo.')
        return redirect(url_for('main.index'))

    file_to_upload = request.files['file']
    original_filename = secure_filename(file_to_upload.filename)
    category = request.form.get('category', 'general').lower() or 'general'

    try:
        # La función put sube el contenido del stream
        blob_data = vercel_blob.put(original_filename, file_to_upload.stream)

        new_file = File(
            filename=blob_data['url'], # Almacenamos la URL del blob
            category=category,
            user_id=session['user_id']
        )
        db.session.add(new_file)
        db.session.commit()
        flash(f'Archivo "{original_filename}" subido correctamente.')
    except Exception as e:
        flash(f'Error al subir archivo a Vercel Blob: {e}')

    return redirect(url_for('main.index', category_name=category))

@main_bp.route('/download/<int:file_id>') # Usamos el ID del archivo, no el nombre, para la descarga
def download_file(file_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    file_to_download = File.query.get_or_404(file_id)

    if not file_to_download.filename: # filename ahora es la URL del blob
        flash('Error: Archivo no encontrado en el almacenamiento.')
        return redirect(url_for('main.index'))
    
    # Redirigir directamente a la URL del blob para la descarga
    return redirect(file_to_download.filename)

@main_bp.route('/delete_file/<int:file_id>')
def delete_file(file_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    file = File.query.get_or_404(file_id)
    
    if session.get('role') != 'admin' and file.user_id != session['user_id']:
        flash('No tienes permiso.')
        return redirect(url_for('main.index'))
        
    try:
        if file.filename: # file.filename es la URL del blob
            vercel_blob.delete(file.filename)
            
        db.session.delete(file)
        db.session.commit()
        flash('Archivo eliminado.')
    except Exception as e:
        flash(f'Error al eliminar: {e}')
        
    return redirect(url_for('main.index'))

# --- CHAT ---

@main_bp.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    content = request.form.get('message')
    if content:
        msg = Message(content=content, user_id=session['user_id'])
        db.session.add(msg)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Empty'}), 400

@main_bp.route('/get_messages')
def get_messages():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    # Polling simple, optimizable
    messages = Message.query.order_by(Message.timestamp.asc()).limit(50).all()
    msgs_data = [{
        'id': m.id,
        'user': m.author.username if m.author else 'Usuario eliminado',
        'text': m.content,
        'edited': m.edited,
        'timestamp': m.timestamp.strftime('%H:%M')
    } for m in messages]
    
    return jsonify(msgs_data)

@main_bp.route('/delete_message/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
        
    msg = Message.query.get(message_id)
    if msg:
        db.session.delete(msg)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404

@main_bp.route('/edit_message/<int:message_id>', methods=['POST'])
def edit_message(message_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
        
    msg = Message.query.get(message_id)
    if msg:
        msg.content = request.form.get('new_text')
        msg.edited = True
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404

# --- DOWNLOADER ---

@main_bp.route('/downloader', methods=['GET', 'POST'])
def downloader():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        video_url = request.form.get('url')
        category = request.form.get('category', 'general').lower() or 'general'
        
        if not video_url:
            flash('Falta URL')
            return redirect(url_for('main.downloader'))
            
        temp_filepath = None
        try:
            if "youtube.com" in video_url or "youtu.be" in video_url:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                    temp_filepath = temp_file.name
                
                ydl_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'outtmpl': temp_filepath, # Descargar al archivo temporal
                    'noplaylist': True,

                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)
                    original_filename = info.get('title', 'youtube_video') + ".mp4"
                
                with open(temp_filepath, 'rb') as f_read:
                    file_content_bytes = f_read.read() # Leer el contenido a bytes
                    blob_data = vercel_blob.put(original_filename, file_content_bytes)
                new_file = File(filename=blob_data['url'], category=category, user_id=session['user_id'])
                db.session.add(new_file)
                db.session.commit()
                flash(f'Video de YouTube descargado y subido: {original_filename}')

            elif "tiktok.com" in video_url:
                host = current_app.config['RAPIDAPI_HOST']
                key = current_app.config['RAPIDAPI_KEY']
                url = f"https://{host}/tiktok/video"
                headers = {"X-RapidAPI-Host": host, "X-RapidAPI-Key": key}
                params = {"url": video_url, "format": "json"}
                
                resp = requests.get(url, headers=headers, params=params)
                data = resp.json()
                
                if data.get('success') and data.get('statusCode') == 200 and data.get('data'):
                    vdata = data['data']
                    link = vdata.get('hdplay') or vdata.get('play')
                    if link:
                        r_vid = requests.get(link, stream=True)
                        r_vid.raise_for_status()

                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                            temp_filepath = temp_file.name
                            for chunk in r_vid.iter_content(8192):
                                temp_file.write(chunk)
                        
                        original_filename = f"tiktok_{int(time.time())}.mp4"
                        with open(temp_filepath, 'rb') as f_read:
                            file_content_bytes = f_read.read() # Leer el contenido a bytes
                            blob_data = vercel_blob.put(original_filename, file_content_bytes)
                        new_file = File(filename=blob_data['url'], category=category, user_id=session['user_id'])
                        db.session.add(new_file)
                        db.session.commit()
                        flash('Video de TikTok descargado y subido.')
                    else:
                        flash('No se encontró enlace de descarga de TikTok.')
                else:
                    flash('Error en la API de TikTok o no se pudo descargar.')

            else:
                flash('URL no soportada. Solo YouTube y TikTok.')
                
        except requests.exceptions.RequestException as e:
            flash(f'Error de red al comunicarse con la API: {e}')
        except Exception as e:
            flash(f'Ocurrió un error inesperado durante la descarga: {e}')
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            
        return redirect(url_for('main.downloader'))

    all_categories = db.session.query(File.category).distinct().all()
    categories = sorted([c[0] for c in all_categories])
    return render_template('main/downloader.html', categories=categories)
