from ftplib import FTP
import os

def conectar_ftp():
    ftp = FTP()
    ftp.connect('tu-servidor-ftp.com', 21)  # Cambia el servidor y puerto
    ftp.login('tu-usuario', 'tu-contraseña')  # Cambia por tus credenciales
    return ftp

def subir_archivo(archivo, carpeta_destino):
    ftp = conectar_ftp()
    archivo_local = os.path.join('ruta/local/del/archivo', archivo)  # Ruta local del archivo
    archivo_remoto = os.path.join(carpeta_destino, archivo)  # Ruta remota en el servidor

    with open(archivo_local, 'rb') as f:
        ftp.storbinary(f'STOR {archivo_remoto}', f)
    print(f"Archivo {archivo} subido con éxito")
    ftp.quit()

# Ejemplo de uso
subir_archivo('documento.pdf', '/uploads')  # Cambia el nombre y la carpeta remota
def es_tipo_archivo_valido(archivo):
    extensiones_permitidas = ['.pdf', '.jpg', '.doc', '.png']
    _, extension = os.path.splitext(archivo)
    return extension.lower() in extensiones_permitidas

def subir_archivo_con_validacion(archivo, carpeta_destino):
    if not es_tipo_archivo_valido(archivo):
        print(f"Tipo de archivo no permitido: {archivo}")
        return

    subir_archivo(archivo, carpeta_destino)
import tkinter as tk
from tkinter import filedialog

def seleccionar_archivo():
    archivo = filedialog.askopenfilename(title="Selecciona un archivo", filetypes=[("Archivos PDF", "*.pdf"), ("Imagenes JPG", "*.jpg"), ("Documentos Word", "*.doc")])
    if archivo:
        print(f"Archivo seleccionado: {archivo}")
        subir_archivo_con_validacion(archivo, '/uploads')  # Subir archivo al servidor

# Configurar la ventana principal
root = tk.Tk()
root.title('Cargar archivo al servidor FTP')
btn_seleccionar = tk.Button(root, text="Seleccionar archivo", command=seleccionar_archivo)
btn_seleccionar.pack(pady=20)
root.mainloop()
