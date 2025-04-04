from datetime import datetime, timezone
import smtplib
import uuid
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_mail import Mail, Message
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import pyodbc
from ftplib import FTP
import imaplib
import email
import traceback # Importar para obtener detalles del error
import logging # Mejor usar logging que print para errores
#############################################################################3

logging.basicConfig(level=logging.ERROR) # Puedes ajustar el nivel (DEBUG, INFO, WARNING, ERROR, CRITICAL)

# Definir las credenciales del correo
EMAIL_USER = '23300101@uttt.edu.mx'
EMAIL_PASS = 'HSG2084H'

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'una_clave_secreta_MUY_segura_y_aleatoria')

# Configuración de la base de datos SQL Server con autenticación de Windows
SERVER = os.getenv('SQL_SERVER', r'DESKTOP-K2COC2B')
DATABASE = os.getenv('SQL_DATABASE', 'datab_base')
DRIVER = '{ODBC Driver 17 for SQL Server}'


# Cadena de conexión con autenticación de Windows
CONNECTION_STRING = f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes'

# Configuración para envío de correos
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '23300101@uttt.edu.mx')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'HSG2084H')
mail = Mail(app)

# Configuración IMAP para recibir correos
IMAP_SERVER = 'imap.gmail.com'
IMAP_USERNAME = 'emanuelcruz123c@gmail.com'  # Cambia esto
IMAP_PASSWORD = 'efnr rkvj fkxd ntwi'  # Cambia esto

# Configuración del servidor FTP
FTP_HOST = 'site18564.siteasp.net'  # Servidor FTP
FTP_USER = 'site18564'              # Usuario FTP
FTP_PASS = 'q+8D!6TtH?y2'           # Contraseña FTP
FTP_PORT = 21                       # Puerto FTP
FTP_UPLOAD_DIR = '/uploads'         # Ruta en el servidor FTP donde se subirán los archivos

# Crear directorio para archivos subidos
# --- Definición de Rutas Robustas ---
UPLOAD_FOLDER_URL_REL = 'static/uploads'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"DEBUG: La ruta base del script (BASE_DIR) es: {BASE_DIR}")
UPLOAD_FOLDER_FILESYSTEM = os.path.join(BASE_DIR, UPLOAD_FOLDER_URL_REL)
print(f"DEBUG: La ruta absoluta para guardar uploads es: {UPLOAD_FOLDER_FILESYSTEM}")

#UPLOAD_FOLDER_URL_REL = 'static/uploads'
#app.config['UPLOAD_FOLDER_URL_REL'] = UPLOAD_FOLDER_URL_REL
#os.makedirs(UPLOAD_FOLDER_URL_REL, exist_ok=True)

ADMIN_EMAIL = '23300101@uttt.edu.mx'

# Crear la conexión a la base de datos
def get_db_connection():
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        return connection
    except pyodbc.Error as e:
        print(f"Error al conectar con la base de datos: {e}")
        return None

# Función para guardar correos en la base de datos
def guardar_correo(asunto, destinatario, cuerpo):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO correo (asunto, destinatario, cuerpo) VALUES (?, ?, ?)", (asunto, destinatario, cuerpo))
        conn.commit()
        cursor.close()
        conn.close()

# --- Funciones Auxiliares ---

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

#################################################################################

# --- FUNCIONES AUXILIARES ---

def send_error_email(error_details):
    """Envía un correo electrónico al administrador con detalles del error."""
    try:
        msg = Message(
            subject="Error en la Aplicación Cartelera",
            sender=app.config['MAIL_USERNAME'],
            recipients=[ADMIN_EMAIL]
        )
        msg.body = f"""
Ha ocurrido un error en la aplicación:

{error_details}
        """
        mail.send(msg)
        app.logger.info("Correo de error enviado al administrador.")
    except Exception as mail_error:
        # Loggear si falla el envío del correo, pero no detener la app por esto
        app.logger.error(f"Error al enviar el correo de notificación: {mail_error}", exc_info=True)


def get_db_connection():
    """Obtiene una conexión a la base de datos con manejo de excepciones."""
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        return connection
    except pyodbc.Error as e:
        # Registrar el error detallado en los logs del servidor
        error_info = traceback.format_exc()
        app.logger.error(f"Error CRÍTICO al conectar con la base de datos: {e}\n{error_info}")
        # Enviar notificación al admin
        send_error_email(f"Error CRÍTICO al conectar con la base de datos: {e}\n{error_info}")
        return None # Devuelve None para indicar fallo

# ... (allowed_file) ...

# --- RUTAS ---

@app.route('/')
def home():
    peliculas_json = [] # Inicializar por si falla la BD
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.titulo, p.fecha_estreno, p.horarios, p.sinopsis,
                       p.trailer_url, g.nombre as genero_nombre, p.imagen_ruta
                FROM pelicula p
                LEFT JOIN genero g ON p.genero_id = g.id
            """)
            peliculas = cursor.fetchall()
            cursor.close()
            conn.close()

            for pelicula in peliculas:
                peliculas_json.append({
                    'id': pelicula.id,
                    'titulo': pelicula.titulo,
                    'fecha': pelicula.fecha_estreno.strftime('%Y-%m-%d') if pelicula.fecha_estreno else '',
                    'horarios': pelicula.horarios,
                    'genero': pelicula.genero_nombre,
                    'sinopsis': pelicula.sinopsis,
                    'imagen': pelicula.imagen_ruta,
                    'trailer': pelicula.trailer_url,
                })
        else:
             # get_db_connection ya habrá loggeado y enviado correo si falló
             flash('No se pudo conectar a la base de datos. Intente más tarde.', 'error')

    except pyodbc.Error as db_error:
        error_info = traceback.format_exc()
        app.logger.error(f"Error de base de datos en /: {db_error}\n{error_info}")
        send_error_email(f"Error de base de datos en /: {db_error}\n{error_info}")
        flash('Ocurrió un error al cargar las películas. Intente más tarde.', 'error')
    except Exception as e: # Captura cualquier otro error inesperado
        error_info = traceback.format_exc()
        app.logger.error(f"Error inesperado en /: {e}\n{error_info}")
        send_error_email(f"Error inesperado en /: {e}\n{error_info}")
        flash('Ocurrió un error inesperado. Intente más tarde.', 'error')

    return render_template('cartelera.html', peliculas=peliculas_json)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                # YA USAS CONSULTAS PARAMETRIZADAS (¡Bien!)
                cursor.execute("SELECT id, nombre_usuario, contraseña FROM usuario WHERE nombre_usuario = ?", (username,))
                user = cursor.fetchone()
                cursor.close()
                conn.close()

                if user:
                    # Asegúrate de usar check_password_hash si las contraseñas están hasheadas
                    # if check_password_hash(user[2], password):
                    if user[2] == password: # Temporal si no has implementado hashing
                        session['user_id'] = user[0]
                        flash('Inicio de sesión exitoso.', 'success')
                        return redirect(url_for('admin'))
                    else:
                        flash('Contraseña incorrecta.', 'error')
                else:
                    flash('Usuario no encontrado.', 'error')
            else:
                flash('Error de conexión. Intente más tarde.', 'error')

        except pyodbc.Error as db_error:
            error_info = traceback.format_exc()
            app.logger.error(f"Error de base de datos en /login: {db_error}\n{error_info}")
            send_error_email(f"Error de base de datos en /login: {db_error}\n{error_info}")
            flash('Error de base de datos al intentar iniciar sesión.', 'error')
        except Exception as e:
            error_info = traceback.format_exc()
            app.logger.error(f"Error inesperado en /login: {e}\n{error_info}")
            send_error_email(f"Error inesperado en /login: {e}\n{error_info}")
            flash('Ocurrió un error inesperado durante el inicio de sesión.', 'error')

        # Si algo falló (excepto el redirect exitoso), volvemos al login
        return render_template('login.html')

    # Si es GET, simplemente muestra el formulario
    return render_template('login.html')


@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    peliculas = []
    generos = []
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.titulo, p.fecha_estreno, g.nombre as genero_nombre, p.imagen_ruta
                FROM pelicula p LEFT JOIN genero g ON p.genero_id = g.id
            """) # Simplificado para la tabla
            peliculas = cursor.fetchall()

            cursor.execute("SELECT id, nombre FROM genero")
            generos = cursor.fetchall()

            cursor.close()
            conn.close()
        else:
            flash('Error de conexión. No se pueden cargar los datos.', 'error')

    except pyodbc.Error as db_error:
        error_info = traceback.format_exc()
        app.logger.error(f"Error de base de datos en /admin: {db_error}\n{error_info}")
        send_error_email(f"Error de base de datos en /admin: {db_error}\n{error_info}")
        flash('Error al cargar los datos del panel de administración.', 'error')
    except Exception as e:
        error_info = traceback.format_exc()
        app.logger.error(f"Error inesperado en /admin: {e}\n{error_info}")
        send_error_email(f"Error inesperado en /admin: {e}\n{error_info}")
        flash('Ocurrió un error inesperado.', 'error')

    return render_template('admin.html', peliculas=peliculas, generos=generos)


@app.route('/admin/peliculas/agregar', methods=['POST'])
def agregar_pelicula():
    if 'user_id' not in session: return redirect(url_for('login'))

    imagen = request.files.get('imagen') # Usar .get para evitar KeyError si no se envía
    if not imagen or imagen.filename == '':
        flash('No se seleccionó ningún archivo de imagen válido.', 'error')
        return redirect(url_for('admin'))

    if not allowed_file(imagen.filename):
        flash('Formato de imagen no permitido.', 'error')
        return redirect(url_for('admin'))

    # Generar nombre único y guardar imagen
    try:
        filename = str(uuid.uuid4()) + '.' + imagen.filename.rsplit('.', 1)[1].lower()
        filepath = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename)
        imagen.save(filepath)
        imagen_ruta = os.path.join('/static/uploads', filename).replace('\\', '/')

    except Exception as file_error:
        error_info = traceback.format_exc()
        app.logger.error(f"Error al guardar la imagen: {file_error}\n{error_info}")
        send_error_email(f"Error al guardar la imagen: {file_error}\n{error_info}")
        flash('Error al guardar la imagen subida.', 'error')
        return redirect(url_for('admin'))

    # Insertar en la base de datos
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pelicula (titulo, fecha_estreno, horarios, sinopsis, trailer_url, genero_id, imagen_ruta)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                request.form.get('titulo'), request.form.get('fecha_estreno'),
                request.form.get('horarios'), request.form.get('sinopsis'),
                request.form.get('trailer_url'), request.form.get('genero_id'),
                imagen_ruta
            ))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Película agregada correctamente.', 'success')
        else:
            flash('Error de conexión. No se pudo agregar la película.', 'error')
            # Considera eliminar la imagen guardada si falla la BD
            try: os.remove(filepath)
            except: pass

    except pyodbc.Error as db_error:
        error_info = traceback.format_exc()
        app.logger.error(f"Error al agregar película a BD: {db_error}\n{error_info}")
        send_error_email(f"Error al agregar película a BD: {db_error}\n{error_info}")
        flash('Error al guardar la información de la película en la base de datos.', 'error')
        # Considera eliminar la imagen guardada si falla la BD
        try: os.remove(filepath)
        except: pass
    except Exception as e:
        error_info = traceback.format_exc()
        app.logger.error(f"Error inesperado al agregar película: {e}\n{error_info}")
        send_error_email(f"Error inesperado al agregar película: {e}\n{error_info}")
        flash('Ocurrió un error inesperado al agregar la película.', 'error')
        # Considera eliminar la imagen guardada si falla la BD
        try: os.remove(filepath)
        except: pass

    return redirect(url_for('admin'))


# --- IMPORTANTE: Aplica try...except de forma similar en - 
###########################################################################33    

#####################################################################3

# ... (Asegúrate de tener las importaciones: traceback, logging, y la función send_error_email) ...

@app.route('/admin/peliculas/editar/<int:id>', methods=['GET', 'POST'])
def editar_pelicula(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = None  # Inicializar conn fuera del try para usarlo en finally
    cursor = None # Inicializar cursor fuera del try para usarlo en finally
    filepath_nueva_imagen = None # Para saber si necesitamos eliminar una imagen nueva en caso de error de BD

    try:
        conn = get_db_connection()
        if not conn:
            flash('Error de conexión. No se pueden cargar/guardar datos.', 'error')
            # get_db_connection ya debería haber loggeado y enviado correo
            return redirect(url_for('admin'))

        cursor = conn.cursor()

        if request.method == 'POST':
            # --- Lógica POST (Guardar Cambios) ---
            titulo = request.form.get('titulo')
            fecha_estreno = request.form.get('fecha_estreno')
            horarios = request.form.get('horarios')
            sinopsis = request.form.get('sinopsis')
            trailer_url = request.form.get('trailer_url')
            genero_id = request.form.get('genero_id')
            imagen = request.files.get('imagen')

            imagen_ruta_actualizar = None # Solo actualizaremos si se sube una nueva imagen

            if imagen and imagen.filename != '' and allowed_file(imagen.filename):
                try:
                    # Guardar nueva imagen
                    filename = str(uuid.uuid4()) + '.' + imagen.filename.rsplit('.', 1)[1].lower()
                    filepath_nueva_imagen = os.path.join(UPLOAD_FOLDER_FILESYSTEM, filename)

                    imagen.save(filepath_nueva_imagen)
                    imagen_ruta_actualizar = f"/{UPLOAD_FOLDER_URL_REL}/{filename}"
                    app.logger.info(f"Nueva imagen guardada temporalmente en: {filepath_nueva_imagen}")
                except Exception as file_error:
                    # Error al guardar el archivo subido
                    error_info = traceback.format_exc()
                    app.logger.error(f"Error al guardar nueva imagen en edición: {file_error}\n{error_info}")
                    send_error_email(f"Error al guardar nueva imagen en edición (ID: {id}): {file_error}\n{error_info}")
                    flash('Error al procesar la nueva imagen.', 'error')
                    # No redirigimos aún, el finally cerrará la conexión
                    return redirect(url_for('admin.editar_pelicula', id=id)) # Volver al form de edición

            # Preparar y ejecutar la consulta UPDATE
            try:
                if imagen_ruta_actualizar:
                    # Si hay nueva imagen, actualizar también la ruta
                    # Podríamos eliminar la imagen antigua aquí si quisiéramos
                    cursor.execute("""
                        UPDATE pelicula
                        SET titulo = ?, fecha_estreno = ?, horarios = ?,
                            sinopsis = ?, trailer_url = ?, genero_id = ?, imagen_ruta = ?
                        WHERE id = ?
                    """, (titulo, fecha_estreno, horarios, sinopsis, trailer_url, genero_id, imagen_ruta_actualizar, id))
                else:
                    # Si no hay nueva imagen, no actualizar la ruta
                    cursor.execute("""
                        UPDATE pelicula
                        SET titulo = ?, fecha_estreno = ?, horarios = ?,
                            sinopsis = ?, trailer_url = ?, genero_id = ?
                        WHERE id = ?
                    """, (titulo, fecha_estreno, horarios, sinopsis, trailer_url, genero_id, id))

                conn.commit()
                flash('Película actualizada correctamente.', 'success')
                return redirect(url_for('admin')) # Redirigir al panel si todo fue bien

            except pyodbc.Error as db_error:
                # Error al actualizar la base de datos
                error_info = traceback.format_exc()
                app.logger.error(f"Error de BD al actualizar película (ID: {id}): {db_error}\n{error_info}")
                send_error_email(f"Error de BD al actualizar película (ID: {id}): {db_error}\n{error_info}")
                flash('Error al guardar los cambios en la base de datos.', 'error')
                # Si guardamos una imagen nueva pero falló la BD, la eliminamos
                if filepath_nueva_imagen:
                    try:
                        os.remove(filepath_nueva_imagen)
                        app.logger.info(f"Imagen nueva eliminada por fallo de BD: {filepath_nueva_imagen}")
                    except Exception as delete_err:
                        app.logger.error(f"No se pudo eliminar imagen nueva tras fallo de BD: {delete_err}")
                return redirect(url_for('admin.editar_pelicula', id=id)) # Volver al form de edición

        else:
            # --- Lógica GET (Mostrar Formulario) ---
            try:
                cursor.execute("SELECT * FROM pelicula WHERE id = ?", (id,))
                pelicula = cursor.fetchone()

                if not pelicula:
                    flash('Película no encontrada.', 'error')
                    return redirect(url_for('admin'))

                cursor.execute("SELECT id, nombre FROM genero")
                generos = cursor.fetchall()

                pelicula_dict = {
                    'id': pelicula[0], 'titulo': pelicula[1], 'fecha_estreno': pelicula[2],
                    'horarios': pelicula[3], 'sinopsis': pelicula[4], 'trailer_url': pelicula[5],
                    'genero_id': pelicula[6], 'imagen_ruta': pelicula[7]
                }
                return render_template('editar_pelicula.html', pelicula=pelicula_dict, generos=generos)

            except pyodbc.Error as db_error:
                # Error al obtener datos para el formulario
                error_info = traceback.format_exc()
                app.logger.error(f"Error de BD al cargar datos para editar (ID: {id}): {db_error}\n{error_info}")
                send_error_email(f"Error de BD al cargar datos para editar (ID: {id}): {db_error}\n{error_info}")
                flash('Error al cargar los datos de la película para editar.', 'error')
                return redirect(url_for('admin'))

    except Exception as e: # Captura cualquier otro error inesperado en la ruta
        error_info = traceback.format_exc()
        app.logger.error(f"Error inesperado en editar_pelicula (ID: {id}): {e}\n{error_info}")
        send_error_email(f"Error inesperado en editar_pelicula (ID: {id}): {e}\n{error_info}")
        flash('Ocurrió un error inesperado al procesar la solicitud.', 'error')
        return redirect(url_for('admin')) # Redirigir a admin como fallback seguro

    finally:
        # Asegurarse de cerrar cursor y conexión
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/admin/peliculas/eliminar/<int:id>', methods=['POST'])
def eliminar_pelicula(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = None
    cursor = None
    imagen_ruta = None
    ruta_completa_imagen = None

    try:
        conn = get_db_connection()
        if not conn:
            flash('Error de conexión. No se pudo eliminar la película.', 'error')
            return redirect(url_for('admin'))

        cursor = conn.cursor()

        # 1. Obtener la ruta de la imagen ANTES de eliminar
        cursor.execute("SELECT imagen_ruta FROM pelicula WHERE id = ?", (id,))
        pelicula_data = cursor.fetchone()
        if pelicula_data:
            imagen_ruta = pelicula_data[0]
            if imagen_ruta: # Construir ruta completa si existe
                 # Usar app.root_path para obtener la ruta base de la aplicación
                ruta_completa_imagen = os.path.join(app.root_path, imagen_ruta)
                # Normalizar separadores por si acaso (opcional pero bueno)
                ruta_completa_imagen = os.path.normpath(ruta_completa_imagen)


        # 2. Eliminar la película de la base de datos
        cursor.execute("DELETE FROM pelicula WHERE id = ?", (id,))
        conn.commit()
        app.logger.info(f"Película ID {id} eliminada de la base de datos.")

        # 3. Eliminar el archivo de imagen del sistema de archivos (si existía)
        if ruta_completa_imagen:
            try:
                os.remove(ruta_completa_imagen)
                app.logger.info(f"Archivo de imagen eliminado: {ruta_completa_imagen}")
                flash('Película y archivo de imagen eliminados correctamente.', 'success')
            except FileNotFoundError:
                app.logger.warning(f"Archivo de imagen no encontrado al intentar eliminar: {ruta_completa_imagen}. Película eliminada de BD de todas formas.")
                flash('Película eliminada de la base de datos (el archivo de imagen no se encontró).', 'warning')
            except OSError as file_error: # Captura otros errores de S.O. al eliminar
                error_info = traceback.format_exc()
                app.logger.error(f"Error de S.O. al eliminar archivo {ruta_completa_imagen}: {file_error}\n{error_info}")
                send_error_email(f"Error de S.O. al eliminar archivo (ID Película: {id}): {file_error}\n{error_info}")
                flash('Película eliminada de la base de datos, pero ocurrió un error al eliminar el archivo de imagen.', 'warning')
        else:
            # No había imagen asociada o no se encontró la ruta en la BD
             if pelicula_data: # Si la pelicula existia en BD
                 flash('Película eliminada correctamente (no tenía imagen asociada).', 'success')
             else:
                 flash('La película no fue encontrada para eliminar.', 'warning')


    except pyodbc.Error as db_error:
        error_info = traceback.format_exc()
        app.logger.error(f"Error de BD al eliminar película (ID: {id}): {db_error}\n{error_info}")
        send_error_email(f"Error de BD al eliminar película (ID: {id}): {db_error}\n{error_info}")
        flash('Error al eliminar la película de la base de datos.', 'error')
    except Exception as e: # Captura cualquier otro error inesperado
        error_info = traceback.format_exc()
        app.logger.error(f"Error inesperado en eliminar_pelicula (ID: {id}): {e}\n{error_info}")
        send_error_email(f"Error inesperado en eliminar_pelicula (ID: {id}): {e}\n{error_info}")
        flash('Ocurrió un error inesperado al intentar eliminar la película.', 'error')

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('admin'))

##########################################################################

# Ruta para el dashboard
@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre_usuario FROM usuario")
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('dashboard.html', usuarios=usuarios)
    return render_template('dashboard.html', usuarios=[])

# --- Rutas de Autenticación (Login) ---
#############################################################
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Elimina la información de sesión
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('home'))

# Ruta para crear un nuevo usuario
@app.route('/crear_usuario', methods=['POST'])
def crear_usuario():
    nombre_usuario = request.form['nombre_usuario']
    contraseña = request.form['contraseña']
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuario (nombre_usuario, contraseña) VALUES (?, ?)", (nombre_usuario, contraseña))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Usuario creado correctamente.')
    return redirect(url_for('dashboard'))

# Ruta para actualizar un usuario
@app.route('/actualizar_usuario/<int:id>', methods=['POST'])
def actualizar_usuario(id):
    nombre_usuario = request.form['nombre_usuario']
    contraseña = request.form['contraseña']
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE usuario SET nombre_usuario = ?, contraseña = ? WHERE id = ?", (nombre_usuario, contraseña, id))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Usuario actualizado correctamente.')
    return redirect(url_for('dashboard'))

# Ruta para eliminar un usuario
@app.route('/eliminar_usuario/<int:id>', methods=['POST'])
def eliminar_usuario(id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuario WHERE id = ?", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Usuario eliminado correctamente.')
    return redirect(url_for('dashboard'))

# Ruta para subir archivos FTP
@app.route('/subir_archivo_ftp', methods=['GET', 'POST'])
def subir_archivo_ftp():
    archivos_subidos = []
    if request.method == 'POST':
        # Subir archivo
        archivo = request.files['archivo']
        if archivo:
            try:
                # Conectar al servidor FTP
                ftp = FTP()
                ftp.connect(FTP_HOST, FTP_PORT)  # Conectar al servidor y puerto
                ftp.login(FTP_USER, FTP_PASS)   # Iniciar sesión
                ftp.cwd(FTP_UPLOAD_DIR)         # Cambiar al directorio de subida

                # Subir el archivo
                ftp.storbinary(f'STOR {archivo.filename}', archivo)
                flash(f'Archivo "{archivo.filename}" subido correctamente.')
            except Exception as e:
                flash(f'Error al subir el archivo: {e}')
            finally:
                ftp.quit()

        # Obtener la lista de archivos subidos
        try:
            ftp = FTP()
            ftp.connect(FTP_HOST, FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.cwd(FTP_UPLOAD_DIR)
            archivos_subidos = ftp.nlst()  # Obtener la lista de archivos
            ftp.quit()
        except Exception as e:
            flash(f'Error al obtener la lista de archivos: {e}')

    return render_template('subir_archivo_ftp.html', archivos=archivos_subidos)

@app.route('/eliminar_archivo_ftp/<nombre>', methods=['POST'])
def eliminar_archivo_ftp(nombre):
    try:
        # Conectar al servidor FTP
        ftp = FTP()
        ftp.connect(FTP_HOST, FTP_PORT)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(FTP_UPLOAD_DIR)

        # Eliminar el archivo
        ftp.delete(nombre)
        flash(f'Archivo "{nombre}" eliminado correctamente.')
    except Exception as e:
        flash(f'Error al eliminar el archivo: {e}')
    finally:
        ftp.quit()

    return redirect(url_for('subir_archivo_ftp'))

# Ruta para listar archivos
@app.route('/archivos')
def archivos():
    # Obtener la lista de archivos en la carpeta de subidas
    archivos = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('archivos.html', archivos=archivos)

# Ruta para eliminar archivos
@app.route('/eliminar_archivo/<nombre>', methods=['POST'])
def eliminar_archivo(nombre):
    try:
        ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], nombre)
        os.remove(ruta_archivo)
        flash(f'Archivo "{nombre}" eliminado correctamente.')
    except Exception as e:
        flash(f'Error al eliminar el archivo: {e}')

    return redirect(url_for('archivos'))

# Ruta para enviar y recibir correos
@app.route('/correos', methods=['GET', 'POST'])
def correos():
    correos_recibidos = []
    
    if request.method == 'POST':
        # Enviar correo
        asunto = request.form['asunto']
        destinatario = request.form['destinatario']
        cuerpo = request.form['cuerpo']

        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_USER
            msg['To'] = destinatario
            msg['Subject'] = asunto
            msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

            server = smtplib.SMTP(IMAP_SERVER, smtplib.SMTP_PORT)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(msg['From'], msg['To'], msg.as_string())
            server.quit()

            flash('Correo enviado correctamente.')
        except Exception as e:
            flash(f'Error al enviar el correo: {e}')
    
    if request.args.get('action') == 'traer_correos':
        try:
            mail_server = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail_server.login(EMAIL_USER, EMAIL_PASS)
            mail_server.select('inbox')

            status, mensajes = mail_server.search(None, 'ALL')
            if status == 'OK':
                lista_mensajes = mensajes[0].split()
                ultimos_100 = lista_mensajes[-100:]
                ultimos_100.reverse()

                for num in ultimos_100:
                    status, datos = mail_server.fetch(num, '(RFC822)')
                    if status == 'OK':
                        mensaje = email.message_from_bytes(datos[0][1])
                        correo_info = {
                            'de': mensaje['from'],
                            'asunto': mensaje['subject'],
                            'fecha': mensaje['date'],
                            'cuerpo': ''
                        }
                        if mensaje.is_multipart():
                            for part in mensaje.walk():
                                if part.get_content_type() == 'text/plain':
                                    correo_info['cuerpo'] = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    break
                        else:
                            correo_info['cuerpo'] = mensaje.get_payload(decode=True).decode('utf-8', errors='ignore')

                        fecha_correo = email.utils.parsedate_to_datetime(correo_info['fecha'])
                        if fecha_correo.tzinfo is None:
                            fecha_correo = fecha_correo.replace(tzinfo=timezone.utc)
                        correo_info['fecha'] = fecha_correo

                        correos_recibidos.append(correo_info)

            mail_server.close()
            mail_server.logout()
        except Exception as e:
            flash(f'Error al recibir correos: {e}')

        correos_recibidos.sort(key=lambda x: x['fecha'], reverse=True)
        return render_template('_correos.html', correos=correos_recibidos)
    
    return render_template('correos.html', correos=correos_recibidos)

# Inicia la aplicación
if __name__ == '__main__':
    app.run(debug=True)
