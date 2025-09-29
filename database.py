"""
Módulo de configuración de la base de datos.
Centraliza la conexión a SQLite para evitar código duplicado.
"""
# DRY: Centralizamos la conexión a la base de datos para evitar código repetido
import sqlite3
from contextlib import contextmanager
from werkzeug.security import generate_password_hash

class Database:
    def __init__(self, db_path='auth_system.db'):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Obtiene una conexión a la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    @contextmanager
    def get_cursor(self):
        """Context manager para manejo automático de conexiones"""
        # KISS: Usamos context manager para simplificar el manejo de recursos
        conn = self.get_connection()
        try:
            yield conn.cursor()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_db(self):
        """Inicializa las tablas de la base de datos"""
        # POLA: Cada tabla tiene una responsabilidad específica y bien definida
        with self.get_cursor() as cursor:
            # Tabla de usuarios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dni TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    status TEXT DEFAULT 'inmaculado',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    login_attempts INTEGER DEFAULT 0,
                    last_attempt TIMESTAMP
                )
            ''')
            
            # Tabla de actividades del sistema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_dni TEXT,
                    action_type TEXT NOT NULL,
                    result TEXT NOT NULL,
                    details TEXT
                )
            ''')
            
            # Insertar usuario administrador por defecto si no existe
            admin_password_hash = generate_password_hash("Password123!")
            cursor.execute('''
                INSERT OR IGNORE INTO users (dni, password_hash, status) 
                VALUES ('admin', ?, 'activo')
            ''', (admin_password_hash,))

# Instancia global de la base de datos
db = Database()