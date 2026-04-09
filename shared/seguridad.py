import jwt
import bcrypt
import os
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("SECRET_KEY", "microservicio_huddle_secret_key_challenge_7_2026_seguro")

# Funciones de seguridad para el servicio de usuario

# Funcion para hashear la contraseña usando bcrypt
def hashear_contraseña(contraseña):
    return bcrypt.hashpw(contraseña.encode(
        ), bcrypt.gensalt()).decode()

# Funcion para verificar la contraseña hasheada
def checkear_contraseña(contraseña_hasheada, contraseña):
    return bcrypt.checkpw(contraseña.encode(), contraseña_hasheada.encode())

# Funcion para gnerar un token JWT para un usuario autenticado
def generar_token(usuario_id):
    ahora = datetime.utcnow()
    payload = {
        "usuario_id": usuario_id,
        "tiempo_emision": int(ahora.timestamp()),
        "tiempo_expiracion": int((ahora + timedelta(hours=24)).timestamp())
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# Funcion para verificar un token JWT y extraer la información del usuario
def verificar_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
