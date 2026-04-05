from flask import Flask, request, jsonify
import os, psycopg2, psycopg2.extras

# Manejo de resiliencia
from shared.resiliencia.retry import retry, parar_despues_de_intentos, esperar_exponencialmente
from shared.resiliencia.circuit_breaker import CircuitBreaker

# Importar la seguridad
import shared.seguridad as seguridad

app = Flask(__name__)
DB_URL = os.getenv("DATABASE_URL")

#crear tabla de pedidos si no existe
def crear_db():
    try: 
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        cursor.execute(""" CREATE TABLE IF NOT EXISTS pedidos (
            id SERIAL PRIMARY KEY,
            usuario_id INT NOT NULL, 
            producto_id INT NOT NULL, 
            cantidad INT NOT NULL, 
            estado VARCHAR (50)
            );
            """)
                 
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ Tabla 'pedidos' creada/verificada correctamente")
    except Exception as e:
        print(f"Error al crear la tabla: {e}")

#Declaramos el manejo de resiliencia
parar = parar_despues_de_intentos(max_intentos= 5)
esperar = esperar_exponencialmente(base= 1)

#Instanciamos el circuit_breaker
circuitBreaker = CircuitBreaker(max_fallas= 5, tiempo_reset= 10, nombre= "PEDIDOS_DB_CB")

#Envolvemos el decorador a la funcion
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

@app.route("/orders", methods=["POST"])
def crear_pedido():
    
    # verificar que el usuario esta autenticado y tiene un token valido
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    payload = seguridad.verificar_token(token)

    if not token:
        return jsonify({"Error": "Token de autorizacion requerido"}), 401

    # Si el token no es valido o ha expirado, devolver un error de autorizacion
    if not payload:
        return jsonify({"Error": "Token de autorizacion invalido o expirado"}), 401 
    
    # Obtener datos del pedido desde la solicitud JSON
    datos = request.get_json()
    usuario_id = payload.get("user_id") or payload.get("usuario_id")
    producto_id = datos.get("producto_id")
    cantidad = datos.get("cantidad")
    estado = "Pendiente"
    
    # Validar que se hayan proporcionado todos los campos necesarios
    if not producto_id or not cantidad:
        return jsonify({"Error": "Faltan campos requeridos"}), 400
    
    # Validar que la cantidad sea un número positivo
    if not isinstance(cantidad, int) or cantidad <= 0:
        return jsonify({"Error": "La cantidad debe ser un número entero positivo"}), 400
    
    # Intentar crear el pedido en la base de datos
    try: 
        # Insertar el nuevo pedido en la base de datos
        query = """INSERT INTO pedidos (usuario_id, producto_id, cantidad, estado) VALUES (%s, %s, %s, %s) 
        RETURNING id;
        """
        
        # Ejecutar la consulta usando la función de resiliencia
        resultado = ejecutar_db(query, (usuario_id, producto_id, cantidad, estado))
        
        # Devolver el ID del nuevo pedido en la respuesta
        return jsonify({"Mensaje": "Pedido creado con exito", 
                       "id": resultado[0][0] if resultado else None}), 201
    # Manejar errores de base de datos o de resiliencia    
    except Exception as e:
        return jsonify({"Error": "Servicio de datos no disponible temporalmente"}), 503

@app.route("/orders", methods=["GET"])
def ver_pedidos():
     # verificar que el usuario esta autenticado y tiene un token valido
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"Error": "Token de autorizacion requerido"}), 401

    payload = seguridad.verificar_token(token)
    # Si el token no es valido o ha expirado, devolver un error de autorizacion
    if not payload:
        return jsonify({"Error": "Token de autorizacion invalido o expirado"}), 401
    
    try:
        # Obtener todos los pedidos de la base de datos
        query = "SELECT * FROM pedidos"
        
        # Ejecutar la consulta usando la función de resiliencia
        resultado = ejecutar_db(query)
        
        # Si existen pedidos, devolverlos
        if resultado:
            pedidos = [dict(row) for row in resultado]
            return jsonify({"Pedidos": pedidos}), 200
        #Sino devolver lista vacia
        else:
            return jsonify({"Pedidos": []}), 200
    except Exception as e: 
        return jsonify({"Error": "Servicio de datos no disponible temporalmente"}), 503


if __name__ == "__main__":
    crear_db()
    app.run(host="0.0.0.0", port=5002, debug=True)