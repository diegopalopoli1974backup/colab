"""
Aplicación principal Flask del sistema de autenticación.
Coordina todas las rutas y funcionalidades del sistema.
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, AdminSystem
from utils import validate_input, format_timestamp, update_user_status_based_on_rules
import re

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'  # En producción usar variable de entorno

# Constantes del sistema
ADMIN_PASSWORD = "Password123!"
BLOCKED_STATUSES = ['bloqueado', 'pausado', 'alertado', 'suspendido']

@app.route('/')
def index():
    """Página principal con menú de opciones"""
    # KISS: Ruta simple que solo muestra el template principal
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de nuevos usuarios"""
    if request.method == 'POST':
        # Validar campos requeridos
        errors = validate_input(request.form, ['dni', 'password', 'confirm_password'])
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html')
        
        dni = request.form['dni']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validar DNI
        is_valid_dni, dni_message = User.validate_dni(dni)
        if not is_valid_dni:
            flash(dni_message, 'error')
            return render_template('register.html')
        
        # Validar que las contraseñas coincidan
        if password != confirm_password:
            flash("Las contraseñas no coinciden", 'error')
            return render_template('register.html')
        
        # Validar contraseña
        is_valid_password, password_message = User.validate_password(password)
        if not is_valid_password:
            flash(password_message, 'error')
            return render_template('register.html')
        
        # Verificar si el usuario ya existe
        if User.find_by_dni(dni):
            flash("El usuario ya existe", 'error')
            return render_template('register.html')
        
        # Crear nuevo usuario
        password_hash = generate_password_hash(password)
        new_user = User(dni=dni, password_hash=password_hash, status='inmaculado')
        new_user.save()
        
        # Registrar actividad
        new_user.log_activity('registro', 'exitoso')
        
        flash("Usuario registrado exitosamente", 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login de usuarios"""
    if request.method == 'POST':
        dni = request.form.get('dni', '')
        password = request.form.get('password', '')
        
        # Validar campos requeridos
        if not dni or not password:
            flash("Por favor complete todos los campos", 'error')
            return render_template('login.html')
        
        # Buscar usuario
        user = User.find_by_dni(dni)
        
        if not user:
            flash("Usuario no encontrado", 'error')
            return render_template('login.html')
        
        # Actualizar estado basado en reglas
        update_user_status_based_on_rules(user)
        
        # Verificar si el usuario puede ingresar
        if user.status in BLOCKED_STATUSES:
            flash(f"Usuario {user.status}. No puede ingresar al sistema.", 'error')
            user.log_activity('acceso', 'fallido', f"Usuario {user.status}")
            return render_template('login.html')
        
        # Verificar contraseña
        if user.check_password(password):
            user.update_login_attempt(True)
            session['user_dni'] = user.dni
            session['is_admin'] = False
            return render_template('success.html')
        else:
            user.update_login_attempt(False)
            flash("Contraseña incorrecta", 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Login de administrador"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if not password:
            flash("Por favor ingrese la contraseña de administrador", 'error')
            return render_template('admin_login.html')
        
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            session['user_dni'] = 'admin'
            
            # Registrar actividad administrativa
            admin_user = User.find_by_dni('admin')
            if admin_user:
                admin_user.log_activity('admin_login', 'exitoso')
            
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Contraseña de administrador incorrecta", 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    """Dashboard administrativo"""
    if not session.get('is_admin'):
        flash("Acceso denegado", 'error')
        return redirect(url_for('index'))
    
    stats = AdminSystem.get_system_stats()
    return render_template('admin.html', stats=stats)

@app.route('/admin/users')
def admin_users():
    """Gestión de usuarios para administradores"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    users = AdminSystem.get_all_users()
    return render_template('admin_users.html', users=users, format_timestamp=format_timestamp)

@app.route('/admin/activities')
def admin_activities():
    """Registro de actividades del sistema"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    activities = AdminSystem.get_all_activities()
    return render_template('admin_activities.html', activities=activities, format_timestamp=format_timestamp)

@app.route('/admin/change_status', methods=['POST'])
def change_user_status():
    """Cambiar estado de un usuario"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    dni = request.form.get('dni')
    new_status = request.form.get('new_status')
    
    if not dni or not new_status:
        return jsonify({'error': 'DNI y nuevo estado son requeridos'}), 400
    
    if dni == 'admin':
        return jsonify({'error': 'No puede modificar el usuario administrador'}), 400
    
    user = User.find_by_dni(dni)
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    if user.status == new_status:
        return jsonify({'error': 'El estado actual y el nuevo no pueden ser idénticos'}), 400
    
    user.status = new_status
    user.save()
    
    # Registrar actividad
    admin_user = User.find_by_dni('admin')
    if admin_user:
        admin_user.log_activity('cambio_estado', 'admin-ok', f"Usuario {dni} -> {new_status}")
    
    return jsonify({'success': True})

@app.route('/admin/change_password', methods=['POST'])
def change_user_password():
    """Cambiar contraseña de un usuario"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    dni = request.form.get('dni')
    new_password = request.form.get('new_password')
    
    if not dni or not new_password:
        return jsonify({'error': 'DNI y nueva contraseña son requeridos'}), 400
    
    user = User.find_by_dni(dni)
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    # Validar nueva contraseña
    is_valid_password, password_message = User.validate_password(new_password)
    if not is_valid_password:
        return jsonify({'error': password_message}), 400
    
    user.password_hash = generate_password_hash(new_password)
    user.save()
    
    # Registrar actividad
    admin_user = User.find_by_dni('admin')
    if admin_user:
        admin_user.log_activity('cambio_password', 'admin-ok', f"Usuario {dni}")
    
    return jsonify({'success': True})

@app.route('/admin/change_admin_password', methods=['POST'])
def change_admin_password():
    """Cambiar contraseña del administrador"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not all([current_password, new_password, confirm_password]):
        return jsonify({'error': 'Todos los campos son requeridos'}), 400
    
    # Verificar contraseña actual
    if current_password != ADMIN_PASSWORD:
        return jsonify({'error': 'Contraseña actual incorrecta'}), 400
    
    # Verificar que las nuevas contraseñas coincidan
    if new_password != confirm_password:
        return jsonify({'error': 'Las nuevas contraseñas no coinciden'}), 400
    
    # Validar nueva contraseña
    is_valid_password, password_message = User.validate_password(new_password)
    if not is_valid_password:
        return jsonify({'error': password_message}), 400
    
    # En una implementación real, aquí actualizarías la contraseña en la base de datos
    # Por ahora, solo mostramos un mensaje de éxito
    admin_user = User.find_by_dni('admin')
    if admin_user:
        admin_user.log_activity('cambio_password_admin', 'admin-ok', 'Contraseña de admin cambiada')
    
    return jsonify({'success': True, 'message': 'Contraseña de administrador actualizada'})

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    # Registrar actividad de logout si hay usuario en sesión
    if session.get('user_dni'):
        user = User.find_by_dni(session['user_dni'])
        if user:
            user.log_activity('logout', 'exitoso')
    
    session.clear()
    flash("Sesión cerrada exitosamente", 'success')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    """Manejo de errores 404"""
    return render_template('error.html', error='Página no encontrada'), 404

@app.errorhandler(500)
def internal_error(error):
    """Manejo de errores 500"""
    return render_template('error.html', error='Error interno del servidor'), 500

def main():
    """Función principal para ejecutar la aplicación"""
    print("=" * 60)
    print("🚀 Sistema de Autenticación - Flask")
    print("=" * 60)
    print("📊 Servidor iniciado correctamente")
    print("🌐 Disponible en: http://localhost:5000")
    print("🔑 Contraseña de administrador: Password123!")
    print("=" * 60)
    print("📍 Endpoints disponibles:")
    print("   /                 - Menú principal")
    print("   /register         - Registro de usuarios")
    print("   /login            - Login de usuarios")
    print("   /admin/login      - Login de administrador")
    print("   /admin/dashboard  - Panel de administración")
    print("   /admin/users      - Gestión de usuarios")
    print("   /admin/activities - Registro de actividades")
    print("=" * 60)
    print("⏹️  Presiona Ctrl+C para detener el servidor")
    print("=" * 60)
    
    # Ejecutar la aplicación con configuración para desarrollo
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # POLA: Separamos la ejecución principal en una función específica
    main()