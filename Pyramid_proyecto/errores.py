from flask import Flask
from flask_mail import Mail, Message

# Crear una instancia de la aplicación Flask
app = Flask(__name__)

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '23300031@uttt.edu.mx'  # Cambia esto por tu correo
app.config['MAIL_PASSWORD'] = 'Dormilon00'  # Cambia esto por tu contraseña

# Inicializar Flask-Mail
mail = Mail(app)

# Contexto de la aplicación para enviar el correo
with app.app_context():
    # Crear el mensaje
    msg = Message(
        subject="Asunto de Prueba",
        sender="23300031@uttt.edu.mx",  # Cambia esto por tu correo
        recipients=["destinatario@example.com"]  # Cambia esto por el destinatario
    )
    msg.body = "Este es un correo de prueba."

    try:
        # Enviar el correo
        mail.send(msg)
        print("Correo enviado correctamente.")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        # Inicia la aplicación
if __name__ == '__main__':
    app.run(debug=True)