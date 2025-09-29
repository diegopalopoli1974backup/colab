"""
Módulo de modelos de datos.
Define las entidades principales del sistema y sus comportamientos.
"""
import sqlite3
from datetime import datetime, timedelta
import re
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

class User:
    """Clase que representa un usuario del sistema"""
    
    def __init__(self, dni, password_hash=None, status='inmaculado', 
                 created_at=None, last_login=None, login_attempts=0, last_attempt=None, id=None):
        # PIE: Constructor expresivo que acepta todos los campos posibles
        self.id = id
        self.dni = dni
        self.password_hash = password_hash
        self.status = status
        self.created_at = created_at
        self.last_login = last_login
        self.login_attempts = login_attempts
        self.last_attempt = last_attempt
    
    @classmethod
    def find_by_dni(cls, dni):
        """Busca un usuario por DNI"""
        # KISS: Método simple y directo para buscar usuarios
        with db.get_cursor() as cursor:
            cursor.execute(
                'SELECT * FROM users WHERE dni = ?', 
                (dni,)
            )
            row = cursor.fetchone()
            if row:
                # DRY: Usamos el mismo método para crear instancias en todo el código
                return cls.create_from_row(row)
        return None
    
    @classmethod
    def create_from_row(cls, row):
        """Crea una instancia de User a partir de una fila de la base de datos"""
        # POLA: Responsabilidad única - crear objetos desde filas de BD
        if not row:
            return None
        
        row_dict = dict(row)
        return cls(
            id=row_dict.get('id'),
            dni=row_dict.get('dni'),
            password_hash=row_dict.get('password_hash'),
            status=row_dict.get('status', 'inmaculado'),
            created_at=row_dict.get('created_at'),
            last_login=row_dict.get('last_login'),
            login_attempts=row_dict.get('login_attempts', 0),
            last_attempt=row_dict.get('last_attempt')
        )
    
    def save(self):
        """Guarda el usuario en la base de datos"""
        with db.get_cursor() as cursor:
            existing_user = User.find_by_dni(self.dni)
            if existing_user and existing_user.id:
                # Actualizar usuario existente
                cursor.execute('''
                    UPDATE users SET 
                    password_hash = ?, status = ?, last_login = ?, 
                    login_attempts = ?, last_attempt = ?
                    WHERE dni = ?
                ''', (self.password_hash, self.status, self.last_login,
                      self.login_attempts, self.last_attempt, self.dni))
            else:
                # Insertar nuevo usuario
                cursor.execute('''
                    INSERT INTO users (dni, password_hash, status)
                    VALUES (?, ?, ?)
                ''', (self.dni, self.password_hash, self.status))
                # Obtener el ID generado
                cursor.execute('SELECT last_insert_rowid()')
                self.id = cursor.fetchone()[0]
    
    @staticmethod
    def validate_dni(dni):
        """
        Valida que el DNI cumpla con los requisitos argentinos
        POLA: Esta función tiene una única responsabilidad: validar formato de DNI
        """
        if not dni:
            return False, "El DNI no puede estar vacío"
        
        if not dni.isdigit():
            return False, "El DNI debe contener solo números"
        
        if len(dni) < 6 or len(dni) > 8:
            return False, "El DNI debe tener entre 6 y 8 dígitos"
        
        return True, "DNI válido"
    
    @staticmethod
    def validate_password(password):
        """
        Valida que la contraseña cumpla con los requisitos de seguridad
        PIE: Separamos la validación en condiciones específicas para mayor claridad
        """
        if len(password) < 8 or len(password) > 12:
            return False, "La contraseña debe tener entre 8 y 12 caracteres"
        
        if not re.search(r'[A-Z]', password):
            return False, "La contraseña debe contener al menos una mayúscula"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "La contraseña debe contener al menos un carácter especial"
        
        return True, "Contraseña válida"
    
    def check_password(self, password):
        """Verifica si la contraseña proporcionada coincide con el hash almacenado"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def update_login_attempt(self, success):
        """Actualiza los intentos de login y el estado del usuario"""
        now = datetime.now().isoformat()
        
        if success:
            self.login_attempts = 0
            self.last_login = now
            self.status = 'activo'
        else:
            self.login_attempts += 1
            self.last_attempt = now
            
            # Verificar si debe ser bloqueado (5 intentos en 1 minuto)
            if self.login_attempts >= 5 and self.last_attempt:
                try:
                    last_attempt_dt = datetime.fromisoformat(self.last_attempt)
                    time_diff = datetime.now() - last_attempt_dt
                    if time_diff < timedelta(minutes=1):
                        self.status = 'bloqueado'
                except ValueError:
                    # En caso de error en el formato de fecha, continuar
                    pass
        
        self.save()
        self.log_activity('acceso', 'exitoso' if success else 'fallido')

    def log_activity(self, action_type, result, details=None):
        """Registra una actividad del sistema"""
        with db.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO activities (user_dni, action_type, result, details)
                VALUES (?, ?, ?, ?)
            ''', (self.dni, action_type, result, details))

class AdminSystem:
    """Clase para manejar las operaciones administrativas"""
    
    @staticmethod
    def get_all_users():
        """Obtiene todos los usuarios del sistema"""
        with db.get_cursor() as cursor:
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            return [User.create_from_row(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_all_activities():
        """Obtiene todas las actividades del sistema"""
        with db.get_cursor() as cursor:
            cursor.execute('SELECT * FROM activities ORDER BY timestamp DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_system_stats():
        """Obtiene estadísticas del sistema"""
        with db.get_cursor() as cursor:
            cursor.execute('SELECT COUNT(*) as total_users FROM users')
            total_users = cursor.fetchone()['total_users']
            
            cursor.execute('SELECT COUNT(*) as total_activities FROM activities')
            total_activities = cursor.fetchone()['total_activities']
            
            return {
                'total_users': total_users,
                'total_activities': total_activities
            }