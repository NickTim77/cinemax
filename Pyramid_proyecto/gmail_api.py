import smtplib
from email.mime.text import MIMEText

def obtener_correos():
    return [
        {"remitente": "23300031@uttt.edu.mx", "asunto": "Correo de prueba"},
        {"remitente": "23300031@uttt.edu.mx", "asunto": "Otro mensaje"}
    ]

def enviar_correo(destinatario, asunto, mensaje):
    remitente = "23300031@uttt.edu.mx"
    password = "Dormilon00"

    msg = MIMEText(mensaje)
    msg["Subject"] = asunto
    msg["From"] = remitente
    msg["To"] = destinatario

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        return "Correo enviado correctamente"
    except Exception as e:
        return f"Error al enviar correo: {str(e)}"
