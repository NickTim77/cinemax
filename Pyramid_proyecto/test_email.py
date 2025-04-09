import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import sys

# Asegurar que el sistema use UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Configuración de credenciales y servidor SMTP
EMAIL_USER = '23300031@uttt.edu.mx'
EMAIL_PASS = 'Dormilon00'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

# Crear el mensaje con codificación UTF-8 explícita
msg = MIMEMultipart()
msg['From'] = EMAIL_USER
msg['To'] = 'fazeji38@gmail.com'
msg['Subject'] = Header('Prueba de envío con acentos', 'utf-8').encode()  # Codificar el asunto en UTF-8

# Definir el cuerpo del mensaje asegurando UTF-8
body = "Este es un correo de prueba con acentos: á, é, í, ó, ú."
msg.attach(MIMEText(body, 'plain', 'utf-8'))  # Asegurar que el texto se codifique correctamente

try:
    # Configurar y conectar al servidor SMTP
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)

    # Enviar el correo
    server.sendmail(EMAIL_USER, 'fazeji38@gmail.com', msg.as_string())

    server.quit()
    print("Correo enviado correctamente")
except Exception as e:
    print(f"Error al enviar el correo: {e}")