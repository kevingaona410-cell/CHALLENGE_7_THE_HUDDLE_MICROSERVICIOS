from flask import Flask, request, jsonify
import os, psycopg2, psycopg2.extras

# Manejo de resiliencia
from shared.resiliencia.retry import retry, parar_despues_de_intentos, esperar_exponencialmente
from shared.resiliencia.circuit_breaker import CircuitBreaker

# Importar la seguridad
import shared.seguridad as seguridad

app = Flask(__name__)
DB_URL = os.getenv("DATABASE_URL")

# En Docker, DOCKER_ENV=true. Si no está definido, asumimos localhost
MODO_DOCKER = os.environ.get("DOCKER_ENV", "").lower() == "true"

# Crear tabla de productos si no existe
def crear_db():
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        cursor.execute(""" CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL UNIQUE,
            precio DECIMAL(10,2) NOT NULL,
            stock INT NOT NULL,
            tipo VARCHAR(50) NOT NULL
            );
            """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ Tabla 'productos' creada/verificada correctamente")
    except Exception as e:
        print(f"Error al crear la tabla: {e}")

# Declaramos el manejo de resiliencia
parar = parar_despues_de_intentos(max_intentos= 5)
esperar = esperar_exponencialmente(base= 1)

# Instanciamos el circuit_breaker
circuitBreaker = CircuitBreaker(max_fallas= 5, tiempo_reset= 10, nombre= "INVENTARIO_DB_CB")

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

# Endpoint para obtener todos los productos
@app.route("/products", methods=["GET"])
def obtener_productos():
    # verificar que el usuario esta autenticado y tiene un token valido
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"Error": "Token de autorizacion requerido"}), 401

    payload = seguridad.verificar_token(token)
    # Si el token no es valido o ha expirado, devolver un error de autorizacion
    if not payload:
        return jsonify({"Error": "Token de autorizacion invalido o expirado"}), 401
    
    try:
        # Obtener todos los productos de la base de datos
        query = "SELECT id, nombre, precio, stock, tipo FROM productos"
        
        # Ejecutar la consulta usando la función de resiliencia
        resultado = ejecutar_db(query)
        
        # Si existen productos, devolverlos
        if resultado:
            productos = [dict(row) for row in resultado]
            return jsonify({"Productos": productos}), 200
        # Sino, devolver lista vacia
        else:
            return jsonify({"Productos": []}), 200
    except Exception as e:
        return jsonify({"Error": "Servicio de datos no disponible temporalmente"}), 503

# Endpoint para crear productos
@app.route("/products", methods=["POST"])        
def crear_producto():
    
    # verificar que el usuario esta autenticado y tiene un token valido
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    payload = seguridad.verificar_token(token)

    if not token:
        return jsonify({"Error": "Token de autorizacion requerido"}), 401

    # Si el token no es valido o ha expirado, devolver un error de autorizacion
    if not payload:
        return jsonify({"Error": "Token de autorizacion invalido o expirado"}), 401 
    
    # Obtener los datos del producto desde la solicitud JSON
    dato = request.get_json() 
    
    nombre = dato.get("nombre")
    precio = dato.get("precio")
    stock = dato.get("stock")
    tipo = dato.get("tipo")
    # Lista de errores
    errores = []
    # Validar los datos del producto
    if not nombre or not isinstance(nombre, str):
        errores.append("nombre es obligatorio y debe ser texto")
    if precio is None:
        errores.append("precio es obligatorio")
    else:
        try:
            precio = float(precio)
            if precio < 0:
                errores.append("precio debe ser un número positivo")

        except (ValueError, TypeError):
            errores.append("precio debe ser un número")
    if stock is None:
        errores.append("stock es obligatorio")
    else:
        try:
            stock = int(stock)
            if stock < 0:
                errores.append("stock debe ser un entero no negativo")

        except (ValueError, TypeError):
            errores.append("stock debe ser un entero")
    if not tipo or not isinstance(tipo, str):
        errores.append("tipo es obligatorio y debe ser texto")
    if errores:
        return jsonify({"Error": errores}), 400
    
    try: 
        # Insertar el nuevo producto en la base de datos
        query = """
        INSERT INTO productos (nombre, precio, stock, tipo) VALUES (%s, %s, %s, %s)
        RETURNING id;        
        """ 
        # Ejecutar la consulta usando la función de resiliencia y obtener el ID del nuevo producto
        resultado = ejecutar_db(query, (nombre, precio, stock, tipo))
        
        # Devolver el ID del nuevo producto en la respuesta
        return jsonify({"Mensaje": "Producto creado con exito", 
                       "id": resultado[0][0] if resultado else None}), 201
    
    # Manejo de errores para producto duplicado y otros errores de la base de datos 
    except psycopg2.errors.UniqueViolation:
        return jsonify({"Error": "El producto ya existe"}), 409
        
    # Manejo de errores generales para errores inesperados    
    except Exception as e:
        return jsonify({"Error": "Servicio de datos no disponible temporalmente"}), 503

# Endpoint para revisar el stock de un producto
@app.route("/stock/<producto>", methods = ["GET"])
def revisar_stock(producto):
     # verificar que el usuario esta autenticado y tiene un token valido
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"Error": "Token de autorizacion requerido"}), 401

    payload = seguridad.verificar_token(token)
    # Si el token no es valido o ha expirado, devolver un error de autorizacion
    if not payload:
        return jsonify({"Error": "Token de autorizacion invalido o expirado"}), 401 
    
    # Obtener el nombre del producto desde la URL y validar que sea un string no vacio    
    try:
        # Obtener el stock del producto de la base de datos
        query = "SELECT stock FROM productos WHERE nombre = %s"
        
        # Ejecutar la consulta usando la función de resiliencia y obtener el ID del nuevo producto
        resultado = ejecutar_db(query, (producto,))
        
        # Si el producto existe, devolver su stock
        if resultado:
            stock = resultado[0]["stock"]
            return jsonify({"Producto": producto, "Stock": stock}), 200
        # Sino, devolver que no se encontro el producto
        else: 
            return jsonify({"Error": "Producto no encontrado"}), 404
    except Exception as e:
        return jsonify({"Error": "Servicio de datos no disponible temporalmente"}), 503

# ====== ENDPOINTS INTERNOS (sin autenticación - para comunicación entre servicios) ======

# Endpoint interno para obtener stock de un producto por ID
@app.route("/internal/stock/<int:producto_id>", methods=["GET"])
def obtener_stock_interno(producto_id):
    """Endpoint sin autenticación para que Pedidos consulte stock"""
    try:
        query = "SELECT id, stock FROM productos WHERE id = %s"
        resultado = ejecutar_db(query, (producto_id,))
        
        if resultado:
            return jsonify({
                "stock": resultado[0]["stock"],
                "disponible": resultado[0]["stock"] > 0
            }), 200
        else:
            return jsonify({"Error": "Producto no encontrado"}), 404
    except Exception as e:
        return jsonify({"Error": "Servicio de datos no disponible"}), 503


if __name__ == "__main__":
    crear_db()  
    app.run(host= "0.0.0.0", port= 5001, debug=True)