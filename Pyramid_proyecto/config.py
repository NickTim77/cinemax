from flask import app, flash, redirect, request, url_for

from app import Usuario


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verifica si el usuario ya existe
        existing_user = Usuario.query.filter_by(username=username).first()
        if existing_user:
            flash('El usuario ya existe. Por favor, elige otro nombre de usuario.', 'warning')
            return redirect(url_for('register'))

        # Crear un nuevo usuario
        nuevo_usuario = Usuario(username=username, password=password)
        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Busca al usuario en la base de datos
        usuario = Usuario.query.filter_by(username=username, password=password).first()

        if usuario:
            session['username'] = usuario.username  # Guarda al usuario en la sesión
            flash(f'Bienvenido, {usuario.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html')
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:  # Verifica si el usuario ha iniciado sesión
        flash('Por favor, inicia sesión para acceder al dashboard.', 'warning')
        return redirect(url_for('login'))

    return render_template('dashboard.html', username=session['username'])
@app.route('/logout')
def logout():
    session.pop('username', None)  # Elimina al usuario de la sesión
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login'))
