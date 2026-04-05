from flask import Flask, request, jsonify
import os, uuid, psycopg2, psycopg2.extras  

# Manejo de resiliencia 
from shared.resiliencia.retry import retry, parar_despues_de_intentos, esperar_exponencialmente
from shared.resiliencia.circuit_breaker import CircuitBreaker

# Importar la seguridad
import shared.seguridad as seguridad

app = Flask(__name__)
DB_URL = os.getenv("DATABASE_URL")

# Crear tabla de usuarios si no existe
def crear_db():
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL UNIQUE,
                contraseña VARCHAR(255) NOT NULL
            );
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ Tabla 'usuarios' creada/verificada correctamente")
    except Exception as e:
        print(f"Error al crear la tabla: {e}")

# Declaramos el manejo de resiliencia
parar = parar_despues_de_intentos(max_intentos = 5)
esperar = esperar_exponencialmente(base = 1)

# Instanciamos el circuit_breaker
circuitBreaker = CircuitBreaker(max_fallas =5, tiempo_reset =10, nombre = "USUARIO_DB_CB")


# Envolvemos el decorador a la funcion 
@retry(parar=parar, esperar = esperar)
@circuitBreaker
def ejecutar_db(query, params=None):
    conexion = psycopg2.connect(DB_URL)
    cursor = conexion.cursor(cursor_factory = psycopg2.extras.DictCursor)
    
    try:
        cursor.execute(query, params)
        conexion.commit()
        # Obtener resultados ANTES de cerrar
        resultados = cursor.fetchall() if query.strip().upper().startswith("SELECT") else None
        return resultados
    
    except Exception as e:
        conexion.rollback()
        raise e
    finally:
        cursor.close()
        conexion.close()

# Endpoint de registro 
@app.route("/register", methods=["POST"])
def registro():
    dato = request.get_json() # Obtener los datos del usuario desde la solicitud JSON
    
    # Validar el nombre y la contraseña
    if not dato.get("nombre") or not dato.get("contraseña"):
        return jsonify({"error" : "Faltan campos"}), 400 
    
    try:
        # Verificar si el usuario ya existe
        usuarios_existentes = ejecutar_db("SELECT * FROM usuarios WHERE nombre = %s", (dato["nombre"],))
        
        if usuarios_existentes:                
            # Si el usuario ya existe, devolver un error
            return jsonify({"error" : "El usuario ya existe"}), 409
        
        # Crear un nuevo usuario con una contraseña hasheada
        contraseña_hash = seguridad.hashear_contraseña(dato["contraseña"])     
        
        # Insertar el nuevo usuario en la base de datos
        ejecutar_db("INSERT INTO usuarios (nombre, contraseña) VALUES (%s, %s)", 
                    (dato["nombre"], contraseña_hash))
        
        return jsonify({"Exito": "Usuario registrado correctamente"}), 201
    except Exception as e:
        return jsonify({"error": "Servicio de datos no disponible temporalmente"}), 503

# Endpoint de login     
@app.route("/login", methods=["POST"])
def login():
    dato = request.get_json() # Obtener los datos del usuario desde la solicitud JSON
    
    # Validar el nombre y la contraseña
    if not dato.get("nombre") or not dato.get("contraseña"):
        return jsonify({"error" : "Faltan campos"}), 400
    
    try:
        # Verificar las credenciales del usuario
        usuarios = ejecutar_db("SELECT * FROM usuarios WHERE nombre = %s", 
                                   (dato["nombre"],))
        
        if not usuarios:
            return jsonify({"Error" : "Credenciales invalidas"}), 401
        
        usuario = usuarios[0]
        
        # Si el usuario existe y la contraseña es correcta, generar un token de autenticación
        if seguridad.checkear_contraseña(usuario["contraseña"], dato["contraseña"]):
            token = seguridad.generar_token(usuario["id"])
            return jsonify ({"Exito": "Bienvenido", "token": token}), 200
        
        # Si la contraseña es incorrecta, devolver un error
        return jsonify ({"Error" : "Credenciales invalidas"}), 401
    except Exception as e:
        return jsonify({"error": "Error interno o base de datos caida"}), 503

if __name__ == "__main__":
    crear_db()  
    app.run(host= "0.0.0.0", port= 5000, debug=True)