import os
import uuid
import smtplib
import imaplib # Si necesitas recibir correos
import email   # Si necesitas procesar correos
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_mail import Mail, Message # Asegúrate que esté descomentado
import pymysql # <--- Conector para MySQL
from pymysql.cursors import DictCursor # Para obtener resultados como diccionarios
from ftplib import FTP # Si necesitas FTP
import traceback
import logging
from functools import wraps
from dotenv import load_dotenv # Para cargar archivo .env localmente

# Cargar variables de entorno desde .env si existe (SOLO para desarrollo local)
# ¡Asegúrate de que .env esté en tu .gitignore!
load_dotenv()

# --- Configuración del Logging ---
logging.basicConfig(level=logging.INFO)

# --- Creación de la App Flask ---
app = Flask(__name__)
# Carga la SECRET_KEY desde variable de entorno ¡CRUCIAL!
app.secret_key = os.getenv('SECRET_KEY')
if not app.secret_key:
    app.logger.critical("¡ERROR FATAL: SECRET_KEY no configurada en variables de entorno!")
    # Considera usar una clave por defecto SOLO si sabes que es seguro para tu caso
    # app.secret_key = 'desarrollo-inseguro-cambiar' # ¡NO USAR EN PRODUCCIÓN!

# --- Configuración de Rutas de Archivos ---
UPLOAD_FOLDER_FILESYSTEM = None # Ruta absoluta para guardar archivos
UPLOAD_FOLDER_URL_REL = 'static/uploads' # Ruta relativa para URLs en HTML/BD
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER_FILESYSTEM = os.path.join(BASE_DIR, UPLOAD_FOLDER_URL_REL)
    os.makedirs(UPLOAD_FOLDER_FILESYSTEM, exist_ok=True)
    app.logger.info(f"Directorio para uploads asegurado en: {UPLOAD_FOLDER_FILESYSTEM}")
except Exception as e:
     app.logger.error(f"¡ERROR CRÍTICO! Creando directorio para uploads: {e}", exc_info=True)
     UPLOAD_FOLDER_FILESYSTEM = None # Marcar como inválido si falla

# --- Configuración de Base de Datos (MySQL con PyMySQL) ---
DB_HOST = os.getenv('DATABASE_HOST')
DB_PORT = int(os.getenv('DATABASE_PORT', 3306)) # Puerto MySQL
DB_NAME = os.getenv('DATABASE_NAME')
DB_USER = os.getenv('DATABASE_USER')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD')

DATABASE_CONFIG_VALID = DB_HOST and DB_NAME and DB_USER and DB_PASSWORD
if not DATABASE_CONFIG_VALID:
    app.logger.critical("¡ERROR FATAL! Faltan variables de entorno para la conexión MySQL (DATABASE_HOST, DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD).")
else:
     app.logger.info(f"Configuración MySQL lista: HOST={DB_HOST}, DB={DB_NAME}, USER={DB_USER}, PORT={DB_PORT}, PWD=****")

# --- Configuración de Correo ---
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME') # Leer de Env Var
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD') # Leer de Env Var
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL') # Leer de Env Var

mail = None
if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD'] and ADMIN_EMAIL:
    try:
        mail = Mail(app)
        app.logger.info("Extensión Flask-Mail inicializada.")
    except Exception as mail_init_error:
        app.logger.error(f"Error al inicializar Flask-Mail: {mail_init_error}", exc_info=True)
else:
     app.logger.warning("Configuración de MAIL incompleta (Falta MAIL_USERNAME, MAIL_PASSWORD o ADMIN_EMAIL en env vars). Envío de correos desactivado.")

# --- Configuración FTP (Si la sigues necesitando) ---
FTP_HOST = os.getenv('FTP_HOST')
FTP_USER = os.getenv('FTP_USER')
FTP_PASS = os.getenv('FTP_PASS')
FTP_PORT = int(os.getenv('FTP_PORT', 21))
FTP_UPLOAD_DIR = os.getenv('FTP_UPLOAD_DIR', '/uploads')

# --- Funciones Auxiliares ---

def get_db_connection():
    """Obtiene una conexión a la base de datos MySQL con PyMySQL."""
    if not DATABASE_CONFIG_VALID:
        app.logger.error("Intento de conexión DB fallido: Configuración MySQL inválida.")
        return None
    try:
        connection = pymysql.connect(host=DB_HOST,
                                     port=DB_PORT,
                                     user=DB_USER,
                                     password=DB_PASSWORD,
                                     database=DB_NAME,
                                     connect_timeout=20,
                                     cursorclass=pymysql.cursors.DictCursor, # Devuelve diccionarios
                                     charset='utf8mb4')
        # app.logger.info("Conexión a MySQL establecida exitosamente.") # Log opcional
        return connection
    except pymysql.Error as e:
        error_info = traceback.format_exc()
        app.logger.error(f"Error CRÍTICO PyMySQL al conectar: {e}\n{error_info}")
        if mail: send_error_email(f"Error CRÍTICO PyMySQL al conectar: {e}\n{error_info}")
        return None
    except Exception as e:
        error_info = traceback.format_exc()
        app.logger.error(f"Error INESPERADO al conectar a MySQL: {e}\n{error_info}")
        if mail: send_error_email(f"Error INESPERADO al conectar a MySQL: {e}\n{error_info}")
        return None

def send_error_email(error_details):
    """Envía un correo electrónico al administrador con detalles del error."""
    global mail, ADMIN_EMAIL
    if not mail:
        app.logger.warning("Intento de enviar correo de error, pero Mail no está inicializado.")
        return
    if not ADMIN_EMAIL:
        app.logger.warning("Intento de enviar correo de error, pero ADMIN_EMAIL no está configurado.")
        return
    try:
        msg = Message(
            subject="Error en Aplicación Cartelera",
            sender=app.config['MAIL_USERNAME'], # Usa la config de Flask
            recipients=[ADMIN_EMAIL]
        )
        msg.body = f"Ha ocurrido un error en la aplicación:\n\n{error_details}"
        mail.send(msg)
        app.logger.info(f"Correo de error enviado a {ADMIN_EMAIL}.")
    except Exception as mail_error:
        app.logger.error(f"Error al enviar el correo de notificación: {mail_error}", exc_info=True)

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# --- Decorador @login_required ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS ---

@app.route('/')
def home():
    # Ruta principal de la cartelera
    peliculas_json = []
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                sql = """
                    SELECT p.id, p.titulo, p.fecha_estreno, p.horarios, p.sinopsis,
                           p.trailer_url, g.nombre as genero_nombre, p.imagen_ruta
                    FROM pelicula p
                    LEFT JOIN genero g ON p.genero_id = g.id
                    ORDER BY p.titulo
                """
                cursor.execute(sql)
                peliculas_raw = cursor.fetchall()

            for pelicula in peliculas_raw:
                 peliculas_json.append({
                    'id': pelicula['id'],
                    'titulo': pelicula['titulo'],
                    'fecha': pelicula['fecha_estreno'].strftime('%Y-%m-%d') if pelicula.get('fecha_estreno') else '',
                    'horarios': pelicula['horarios'],
                    'genero': pelicula['genero_nombre'],
                    'sinopsis': pelicula['sinopsis'],
                    'imagen': pelicula['imagen_ruta'],
                    'trailer': pelicula['trailer_url'],
                })
        else:
             flash('No se pudo conectar a la base de datos para cargar películas.', 'error')

    except pymysql.Error as db_error:
        error_info = traceback.format_exc(); app.logger.error(f"Error BD(MySQL) en /: {db_error}\n{error_info}")
        if mail: send_error_email(...)
        flash('Ocurrió un error al cargar las películas.', 'error')
    except Exception as e:
        error_info = traceback.format_exc(); app.logger.error(f"Error inesperado en /: {e}\n{error_info}")
        if mail: send_error_email(...)
        flash('Ocurrió un error inesperado.', 'error')
    finally:
        if conn and conn.open: conn.close()

    # Cambiado a index.html, asumiendo que es tu plantilla principal
    return render_template('index.html', peliculas=peliculas_json)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password') # ¡Necesitas HASHING!

        if not username or not password:
             flash('Usuario y contraseña son requeridos.', 'warning')
             return render_template('login.html')

        conn = None
        user_data = None
        try:
            conn = get_db_connection()
            if conn:
                with conn.cursor() as cursor:
                    sql = "SELECT id, nombre_usuario, contraseña FROM usuario WHERE nombre_usuario = %s" # <-- %s
                    cursor.execute(sql, (username,))
                    user_data = cursor.fetchone()

                if user_data:
                    # *** ¡IMPLEMENTAR HASHING AQUÍ! ***
                    # stored_hash = user_data['contraseña']
                    # from werkzeug.security import check_password_hash
                    # if check_password_hash(stored_hash, password):
                    if user_data['contraseña'] == password: # ¡INSEGURO!
                        session.permanent = True
                        session['user_id'] = user_data['id']
                        session['username'] = user_data['nombre_usuario']
                        flash(f'Inicio de sesión exitoso. ¡Bienvenido {user_data["nombre_usuario"]}!', 'success')
                        return redirect(url_for('admin'))
                    else:
                        flash('Contraseña incorrecta.', 'error')
                else:
                    flash('Usuario no encontrado.', 'error')
            else:
                flash('Error de conexión BD.', 'error')

        except pymysql.Error as db_error:
            error_info = traceback.format_exc(); app.logger.error(f"Error BD(MySQL) en /login: {db_error}\n{error_info}")
            if mail: send_error_email(...)
            flash('Error al verificar credenciales.', 'error')
        except Exception as e:
            error_info = traceback.format_exc(); app.logger.error(f"Error inesperado en /login: {e}\n{error_info}")
            if mail: send_error_email(...)
            flash('Error inesperado durante el login.', 'error')
        finally:
            if conn and conn.open: conn.close()

        return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('login'))

# --- RUTAS DE ADMINISTRACIÓN ---

@app.route('/admin')
@login_required
def admin():
    peliculas = []
    generos = []
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                sql_peliculas = """
                    SELECT p.id, p.titulo, p.fecha_estreno, p.horarios,
                           g.nombre as genero_nombre, p.imagen_ruta
                    FROM pelicula p
                    LEFT JOIN genero g ON p.genero_id = g.id
                    ORDER BY p.titulo
                """
                cursor.execute(sql_peliculas)
                peliculas = cursor.fetchall()

                sql_generos = "SELECT id, nombre FROM genero ORDER BY nombre"
                cursor.execute(sql_generos)
                generos = cursor.fetchall()
        else:
            flash('Error conexión BD. No se cargaron datos.', 'error')

    except pymysql.Error as db_error:
        error_info = traceback.format_exc(); app.logger.error(f"Error BD(MySQL) en /admin: {db_error}\n{error_info}")
        if mail: send_error_email(...)
        flash('Error al cargar datos del panel.', 'error')
    except Exception as e:
        error_info = traceback.format_exc(); app.logger.error(f"Error inesperado en /admin: {e}\n{error_info}")
        if mail: send_error_email(...)
        flash('Error inesperado en panel.', 'error')
    finally:
        if conn and conn.open: conn.close()

    return render_template('admin.html', peliculas=peliculas, generos=generos)


@app.route('/admin/peliculas/agregar', methods=['POST'])
@login_required # Aplicar decorador
def agregar_pelicula():
    # La verificación de sesión ya la hace el decorador
    imagen = request.files.get('imagen')
    filepath = None # Ruta absoluta para guardar/borrar archivo, inicializar a None
    imagen_ruta = None # Ruta relativa URL para BD, inicializar a None

    # Validaciones iniciales
    if not imagen or imagen.filename == '':
        flash('No se seleccionó ningún archivo de imagen válido.', 'error')
        return redirect(url_for('admin'))
    if not allowed_file(imagen.filename):
        flash('Formato de imagen no permitido.', 'error')
        return redirect(url_for('admin'))
    # Verificar si la carpeta de uploads es válida (se definió al inicio)
    if not UPLOAD_FOLDER_FILESYSTEM:
         flash('Error interno: La configuración de la carpeta de subida no es válida.', 'error')
         return redirect(url_for('admin'))

    # Procesar y guardar imagen
    try:
        filename = str(uuid.uuid4()) + '.' + imagen.filename.rsplit('.', 1)[1].lower()
        # Usar la ruta absoluta del sistema para guardar
        filepath = os.path.join(UPLOAD_FOLDER_FILESYSTEM, filename)
        # Usar la ruta relativa URL para la BD
        imagen_ruta = f"/{UPLOAD_FOLDER_URL_REL}/{filename}"

        app.logger.info(f"Intentando guardar imagen en: {filepath}")
        imagen.save(filepath)
        app.logger.info(f"Imagen guardada exitosamente en: {filepath}")

    except Exception as file_error:
        # Error al intentar guardar el archivo en el servidor
        error_info = traceback.format_exc()
        app.logger.error(f"Error al guardar la imagen: {file_error}\n{error_info}")
        # Comentar/descomentar si Flask-Mail funciona
        if mail: send_error_email(f"Error al guardar la imagen: {file_error}\n{error_info}")
        flash('Error al guardar la imagen subida en el servidor.', 'error')
        # No hay archivo que borrar si falló aquí, redirigir directamente
        return redirect(url_for('admin'))

    # Si llegamos aquí, la imagen se guardó. Ahora intentamos insertar en BD.
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                # Usar %s para parámetros con PyMySQL
                sql = """
                    INSERT INTO pelicula
                    (titulo, fecha_estreno, horarios, sinopsis, trailer_url, genero_id, imagen_ruta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                fecha_estreno_val = request.form.get('fecha_estreno') or None
                genero_id_val = request.form.get('genero_id') or None
                if genero_id_val: genero_id_val = int(genero_id_val) # Convertir a int

                params = (
                    request.form.get('titulo'), fecha_estreno_val, request.form.get('horarios'),
                    request.form.get('sinopsis'), request.form.get('trailer_url'),
                    genero_id_val, imagen_ruta
                )
                cursor.execute(sql, params)
            conn.commit() # Commit DESPUÉS del bloque 'with cursor'
            flash('Película agregada correctamente.', 'success')
        else:
            # Falló get_db_connection()
            flash('Error conexión BD. No se pudo agregar la película.', 'error')
            # --- BLOQUE CORREGIDO ---
            # Intentar borrar la imagen porque la conexión falló DESPUÉS de guardarla
            if filepath:
                try:
                    os.remove(filepath)
                    app.logger.info(f"Imagen {filepath} borrada por fallo de conexión BD.")
                except Exception as del_err:
                    app.logger.error(f"Error borrando {filepath} tras fallo conexión BD: {del_err}")
            # --- FIN BLOQUE CORREGIDO ---

    except (pymysql.Error, ValueError) as db_error: # Capturar error PyMySQL y ValueError de int()
        error_info = traceback.format_exc()
        app.logger.error(f"Error BD/Valor al agregar película: {db_error}\n{error_info}")
        if mail: send_error_email(...)
        flash('Error al guardar la película en la base de datos.', 'error')

        # --- BLOQUE CORREGIDO ---
        # Intentar borrar la imagen si falló la inserción/commit en BD
        if filepath:
            try:
                os.remove(filepath)
                app.logger.info(f"Imagen {filepath} borrada por fallo de BD al agregar.")
            except Exception as delete_err:
                app.logger.error(f"No se pudo eliminar imagen {filepath} tras fallo de BD: {delete_err}")
        # --- FIN BLOQUE CORREGIDO ---

    except Exception as e: # Otros errores inesperados
        error_info = traceback.format_exc()
        app.logger.error(f"Error inesperado al agregar película: {e}\n{error_info}")
        if mail: send_error_email(...)
        flash('Ocurrió un error inesperado al agregar la película.', 'error')

        # --- BLOQUE CORREGIDO ---
        # Intentar borrar la imagen si falló por otra razón
        if filepath:
            try:
                os.remove(filepath)
                app.logger.info(f"Imagen {filepath} borrada por error inesperado.")
            except Exception as delete_err:
                app.logger.error(f"No se pudo eliminar imagen {filepath} tras error inesperado: {delete_err}")
        # --- FIN BLOQUE CORREGIDO ---

    finally:
         # Asegurarse de cerrar la conexión si se abrió
         if conn and conn.open:
             conn.close()

    # Redirigir a admin después de éxito o error manejado
    # Este redirect debe estar fuera del finally, pero alcanzarse si hubo éxito o error
    return redirect(url_for('admin'))


@app.route('/admin/peliculas/editar/<int:id>', methods=['GET', 'POST'])
@login_required # Aplicar decorador
def editar_pelicula(id):
    conn = None
    cursor = None
    # Ruta absoluta si se guarda una NUEVA imagen en este request
    filepath_nueva_imagen = None

    try:
        conn = get_db_connection()
        if not conn:
            flash('Error de conexión BD al intentar editar.', 'error')
            return redirect(url_for('admin'))

        # No necesitamos cursor para POST aún, pero sí para GET
        # cursor = conn.cursor() # <-- Mover dentro del bloque GET o usar 'with'

        if request.method == 'POST':
            # --- Proceso POST ---
            titulo = request.form.get('titulo')
            fecha_estreno = request.form.get('fecha_estreno') or None
            horarios = request.form.get('horarios')
            sinopsis = request.form.get('sinopsis')
            trailer_url = request.form.get('trailer_url')
            genero_id = request.form.get('genero_id') or None
            if genero_id:
                try:
                    genero_id = int(genero_id)
                except ValueError:
                    flash('ID de género inválido.', 'error')
                    return redirect(url_for('admin.editar_pelicula', id=id)) # Volver al form

            imagen = request.files.get('imagen')
            imagen_ruta_para_bd = None # Ruta URL relativa si se sube nueva imagen

            # 1. Procesar nueva imagen si existe
            if imagen and imagen.filename != '' and allowed_file(imagen.filename):
                if not UPLOAD_FOLDER_FILESYSTEM:
                     flash('Error config: Carpeta uploads no encontrada.', 'error')
                     return redirect(url_for('admin')) # Fallo crítico de config
                try:
                    # TODO: Considerar borrar la imagen *anterior* si esta se guarda bien
                    filename = str(uuid.uuid4()) + '.' + imagen.filename.rsplit('.', 1)[1].lower()
                    filepath_nueva_imagen = os.path.join(UPLOAD_FOLDER_FILESYSTEM, filename)
                    imagen_ruta_para_bd = f"/{UPLOAD_FOLDER_URL_REL}/{filename}" # Ruta URL
                    app.logger.info(f"Intentando guardar nueva imagen en: {filepath_nueva_imagen}")
                    imagen.save(filepath_nueva_imagen)
                    app.logger.info(f"Nueva imagen guardada exitosamente.")
                except Exception as file_error:
                    # Falló el guardado del archivo nuevo
                    error_info = traceback.format_exc()
                    app.logger.error(f"Error al guardar nueva imagen en edición {id}: {file_error}\n{error_info}")
                    if mail: send_error_email(...)
                    flash('Error al procesar la nueva imagen. Cambios NO guardados.', 'error')
                    return redirect(url_for('admin')) # Redirige a admin si falla guardar la imagen

            # 2. Actualizar Base de Datos
            try:
                 with conn.cursor() as cursor: # Abrir cursor aquí para el UPDATE
                    if imagen_ruta_para_bd: # Si se guardó una imagen nueva y se preparó su ruta para BD
                        # Actualizar TODO incluyendo imagen_ruta
                        sql = """
                            UPDATE pelicula SET titulo=%s, fecha_estreno=%s, horarios=%s,
                                  sinopsis=%s, trailer_url=%s, genero_id=%s, imagen_ruta=%s
                            WHERE id=%s
                        """
                        params = (titulo, fecha_estreno, horarios, sinopsis, trailer_url, genero_id, imagen_ruta_para_bd, id)
                    else: # Si no se subió imagen nueva
                        # Actualizar TODO EXCEPTO imagen_ruta
                        sql = """
                            UPDATE pelicula SET titulo=%s, fecha_estreno=%s, horarios=%s,
                                  sinopsis=%s, trailer_url=%s, genero_id=%s
                            WHERE id=%s
                        """
                        params = (titulo, fecha_estreno, horarios, sinopsis, trailer_url, genero_id, id)

                    cursor.execute(sql, params)
                 conn.commit() # Commit después del 'with cursor'
                 flash('Película actualizada correctamente.', 'success')
                 # Éxito, cerrar conexión en finally y redirigir
                 return redirect(url_for('admin'))

            except (pymysql.Error, ValueError) as db_error: # Error de BD o conversión de género ID
                error_info = traceback.format_exc()
                app.logger.error(f"Error BD/Valor al actualizar película {id}: {db_error}\n{error_info}")
                if mail: send_error_email(...)
                flash('Error al guardar los cambios en la base de datos.', 'error')

                # --- INICIO BLOQUE CORREGIDO (para except db_error) ---
                # Si falló la BD pero sí guardamos una imagen nueva, borrarla
                if filepath_nueva_imagen:
                    try:
                        os.remove(filepath_nueva_imagen)
                        app.logger.info(f"Imagen nueva {filepath_nueva_imagen} borrada por fallo de BD.")
                    except Exception as delete_err:
                        app.logger.error(f"No se pudo eliminar imagen {filepath_nueva_imagen} tras fallo de BD: {delete_err}")
                # --- FIN BLOQUE CORREGIDO ---

                # Después del error de BD, redirigir a admin
                return redirect(url_for('admin'))

        else: # --- Proceso GET (Mostrar formulario para editar) ---
            try:
                with conn.cursor() as cursor: # Abrir cursor para el SELECT
                    # Obtener datos de la película Y el nombre del género
                    sql_pelicula = """
                        SELECT p.*, g.nombre as genero_nombre
                        FROM pelicula p
                        LEFT JOIN genero g ON p.genero_id = g.id
                        WHERE p.id = %s
                    """ # <-- %s para PyMySQL
                    cursor.execute(sql_pelicula, (id,))
                    pelicula = cursor.fetchone() # Devuelve diccionario

                    if not pelicula:
                        flash('Película no encontrada.', 'error')
                        return redirect(url_for('admin'))

                    # Obtener lista de géneros para el dropdown
                    cursor.execute("SELECT id, nombre FROM genero ORDER BY nombre")
                    generos = cursor.fetchall() # Lista de diccionarios

                # Formatear fecha para input type="date"
                pelicula['fecha_estreno_fmt'] = pelicula['fecha_estreno'].strftime('%Y-%m-%d') if pelicula.get('fecha_estreno') else ''

                # Renderizar la plantilla pasando los datos
                return render_template('editar_pelicula.html', pelicula=pelicula, generos=generos)

            except pymysql.Error as db_error: # <-- Capturar error PyMySQL
                 error_info = traceback.format_exc()
                 app.logger.error(f"Error de BD al cargar datos para editar {id}: {db_error}\n{error_info}")
                 if mail: send_error_email(...)
                 flash('Error al cargar los datos de la película para editar.', 'error')
                 return redirect(url_for('admin')) # Redirigir si falla carga GET

    # Captura general de errores inesperados en la ruta (fuera del POST/GET específico)
    except Exception as e:
        error_info = traceback.format_exc()
        app.logger.error(f"Error inesperado en editar_pelicula {id}: {e}\n{error_info}")
        if mail: send_error_email(...)
        flash('Ocurrió un error inesperado al procesar la solicitud de edición.', 'error')

        # --- INICIO BLOQUE CORREGIDO (para except Exception as e general) ---
        # Si ocurrió un error inesperado DESPUÉS de guardar una nueva imagen (poco probable pero posible)
        if filepath_nueva_imagen:
             try:
                 os.remove(filepath_nueva_imagen)
                 app.logger.info(f"Imagen nueva {filepath_nueva_imagen} borrada por error inesperado.")
             except Exception as delete_err:
                 app.logger.error(f"No se pudo eliminar imagen {filepath_nueva_imagen} tras error inesperado: {delete_err}")
        # --- FIN BLOQUE CORREGIDO ---

        return redirect(url_for('admin')) # Redirigir a admin como fallback seguro

    finally:
        # Asegurarse de cerrar la conexión en todos los casos donde se abrió
        if conn and conn.open:
            conn.close()
            app.logger.debug(f"Conexión MySQL cerrada en /admin/peliculas/editar/{id} finally")


@app.route('/admin/peliculas/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_pelicula(id):
    conn = None
    filepath_absoluta_fs = None
    imagen_ruta_relativa_url = None

    try:
        conn = get_db_connection()
        if not conn: flash('Error conexión BD.', 'error'); return redirect(url_for('admin'))

        with conn.cursor() as cursor:
            # 1. Obtener ruta de imagen ANTES de borrar
            cursor.execute("SELECT imagen_ruta FROM pelicula WHERE id = %s", (id,)) # <-- %s
            pelicula_data = cursor.fetchone()
            if pelicula_data and pelicula_data.get('imagen_ruta'):
                imagen_ruta_relativa_url = pelicula_data['imagen_ruta']
                if imagen_ruta_relativa_url.startswith(f"/{UPLOAD_FOLDER_URL_REL}/"):
                    path_relative_to_static = imagen_ruta_relativa_url.lstrip('/')
                    filepath_absoluta_fs = os.path.join(BASE_DIR, path_relative_to_static)
                    filepath_absoluta_fs = os.path.normpath(filepath_absoluta_fs)
                else:
                     app.logger.warning(f"Formato imagen_ruta inesperado {id}: {imagen_ruta_relativa_url}")
                     filepath_absoluta_fs = None

            # 2. Eliminar registro de la BD
            sql_delete = "DELETE FROM pelicula WHERE id = %s" # <-- %s
            rows_affected = cursor.execute(sql_delete, (id,))

        conn.commit()

        # 3. Intentar borrar archivo físico si corresponde
        if rows_affected > 0:
            app.logger.info(f"Película ID {id} eliminada de BD ({rows_affected} filas).")
            if filepath_absoluta_fs:
                try:
                    app.logger.info(f"Intentando borrar archivo: {filepath_absoluta_fs}")
                    os.remove(filepath_absoluta_fs)
                    flash('Película y archivo imagen eliminados.', 'success')
                except FileNotFoundError:
                    app.logger.warning(f"Archivo no encontrado al borrar: {filepath_absoluta_fs}.")
                    flash('Película eliminada (archivo imagen no encontrado).', 'warning')
                except OSError as file_error:
                    error_info = traceback.format_exc(); app.logger.error(f"Error OS al eliminar {filepath_absoluta_fs}: {file_error}\n{error_info}")
                    if mail: send_error_email(...)
                    flash('Película eliminada, pero error al borrar archivo.', 'warning')
            elif pelicula_data:
                 flash('Película eliminada (sin imagen asociada).', 'success')
            else:
                 flash('Película no encontrada para eliminar.', 'warning')
        else:
             flash('La película no fue encontrada o no se pudo eliminar.', 'warning')

    except pymysql.Error as db_error: # <-- CAMBIO: Capturar error PyMySQL
        error_info = traceback.format_exc(); app.logger.error(f"Error BD (MySQL) al eliminar {id}: {db_error}\n{error_info}")
        if mail: send_error_email(...)
        flash('Error al eliminar película de BD.', 'error')
    except Exception as e:
        error_info = traceback.format_exc(); app.logger.error(f"Error inesperado al eliminar {id}: {e}\n{error_info}")
        if mail: send_error_email(...)
        flash('Error inesperado al eliminar.', 'error')
    finally:
        if conn and conn.open: conn.close()

    return redirect(url_for('admin'))


# --- Rutas de USUARIO y OTRAS (COMENTADAS - NECESITAN ADAPTACIÓN A PYMYSQL Y HASHING) ---
# ... (Mantener comentadas o adaptar/eliminar) ...


# --- Punto de Entrada (SOLO para desarrollo local si es necesario) ---
if __name__ == '__main__':
    print("ADVERTENCIA: Ejecutando en modo de desarrollo local.")
    # Comprobar si se pudo construir la cadena de conexión para dar feedback
    if DATABASE_CONFIG_VALID and CONNECTION_STRING:
         print(f"Configuración de BD (MySQL) detectada para: {DB_HOST}/{DB_NAME}")
    elif not DATABASE_CONFIG_VALID:
         print("ERROR LOCAL: Faltan variables de entorno de BD (DATABASE_HOST, etc.). Define un .env o usa 'set'/'export'.")
    else:
         print("ADVERTENCIA LOCAL: No se pudo construir CONNECTION_STRING, revisa la lógica.")

    port = int(os.environ.get('PORT', 5000))
    # Ejecutar con debug=False siempre es más seguro, incluso localmente
    # Para ver errores locales, confía en el logging y el traceback en la terminal
    app.run(debug=False, host='0.0.0.0', port=port)
