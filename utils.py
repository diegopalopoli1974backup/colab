"""
Módulo de utilidades generales.
Contiene funciones auxiliares reutilizables en todo el sistema.
"""
import re
from datetime import datetime, timedelta
from database import db

# DRY: Centralizamos funciones de validación y formateo que se usan en múltiples lugares
def validate_input(data, required_fields):
    """
    Valida que los campos requeridos estén presentes y no estén vacíos
    KISS: Función simple que hace una sola cosa bien
    """
    errors = []
    for field in required_fields:
        if field not in data or not data[field].strip():
            errors.append(f"El campo {field} es requerido")
    return errors

def format_timestamp(timestamp):
    """Formatea un timestamp para mostrar de manera legible"""
    if not timestamp:
        return "Nunca"
    
    try:
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return "Fecha inválida"

def check_consecutive_failed_logins(dni, days=5):
    """
    Verifica si un usuario ha tenido intentos fallidos consecutivos
    PIE: Separamos la lógica compleja en pasos comprensibles
    """
    with db.get_cursor() as cursor:
        recent_attempts = cursor.execute('''
            SELECT DATE(timestamp) as attempt_date, COUNT(*) as failures
            FROM activities 
            WHERE user_dni = ? AND action_type = 'acceso' AND result = 'fallido'
            AND timestamp >= DATE('now', ?)
            GROUP BY DATE(timestamp)
            ORDER BY attempt_date DESC
            LIMIT ?
        ''', (dni, f'-{days} days', days)).fetchall()
        
        # Verificar si tenemos exactamente 'days' días consecutivos con fallos
        if len(recent_attempts) >= days:
            expected_dates = [
                (datetime.now() - timedelta(days=i)).date() 
                for i in range(days)
            ]
            
            actual_dates = []
            for row in recent_attempts[:days]:
                try:
                    date_obj = datetime.fromisoformat(row['attempt_date']).date()
                    actual_dates.append(date_obj)
                except ValueError:
                    continue
            
            return actual_dates == expected_dates
        
    return False

def update_user_status_based_on_rules(user):
    """
    Actualiza el estado del usuario basado en las reglas del negocio
    POLA: Esta función tiene una única responsabilidad: aplicar reglas de estado
    """
    if not user:
        return
    
    now = datetime.now()
    
    # Regla: pausado (último login hace más de 6 meses)
    if user.last_login:
        try:
            last_login_dt = datetime.fromisoformat(user.last_login)
            if (now - last_login_dt) > timedelta(days=180):
                user.status = 'pausado'
        except ValueError:
            # Si hay error en el formato, ignorar
            pass
    
    # Regla: alertado (5 días consecutivos con intentos fallidos)
    elif check_consecutive_failed_logins(user.dni):
        user.status = 'alertado'
    
    user.save()