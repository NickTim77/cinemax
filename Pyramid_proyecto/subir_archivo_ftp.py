from flask import Flask, render_template, request, redirect, session, url_for, flash
import os
from ftplib import FTP

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Configuración del servidor FTP
FTP_HOST = 'ftp.tuservidor.com'
FTP_USER = 'tu_usuario_ftp'
FTP_PASS = 'tu_contraseña_ftp'
FTP_UPLOAD_DIR = '/ruta/del/servidor/ftp'  # Ruta en el servidor FTP donde se subirán los archivos

# Ruta para subir archivos
@app.route('/subir_archivo_ftp', methods=['GET', 'POST'])
def subir_archivo_ftp():
    if 'username' not in session:
        flash('Debes iniciar sesión primero.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        archivo = request.files['archivo']
        if archivo:
            try:
                # Conectar al servidor FTP
                ftp = FTP(FTP_HOST)
                ftp.login(FTP_USER, FTP_PASS)
                ftp.cwd(FTP_UPLOAD_DIR)

                # Subir el archivo
                ftp.storbinary(f'STOR {archivo.filename}', archivo)
                ftp.quit()

                flash('Archivo subido correctamente.')
            except Exception as e:
                flash(f'Error al subir el archivo: {e}')

            return redirect(url_for('dashboard'))

    return render_template('subir_archivo_ftp.html')