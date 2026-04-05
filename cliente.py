import requests, os, json

# Modo docker para usar los nombres de host de los servicios en lugar de localhost
MODO_DOCKER = os.environ.get("DOCKER_ENV")

# URLs de los servicios, usando los nombres de host si estamos en modo docker
URL_SERVICIO_USUARIO = "http://servicio-user:5000"  if MODO_DOCKER else "http://localhost:5000"
URL_SERVICIO_INVENTARIO = "http://servicio-inventario:5001" if MODO_DOCKER else "http://localhost:5001"
URL_SERVICIO_PEDIDOS = "http://servicio-pedidos:5002" if MODO_DOCKER else "http://localhost:5002"

# Función para registrar un nuevo usuario
def registrar_usuario(): 
    print("\n--- Registro ---")
    nombre = input("Nombre: ")
    contraseña = input("Contraseña: ")
    
    # Enviar una solicitud POST al servicio de usuario para registrar un nuevo usuario
    try:
        respuesta = requests.post(f"{URL_SERVICIO_USUARIO}/register", 
                                  json={"nombre": nombre, "contraseña": contraseña})
        # Si el registro es exitoso, mostrar el mensaje de éxito
        if respuesta.status_code == 200 or respuesta.status_code == 201:
            print(f"Exito: {respuesta.json()}", respuesta.status_code)
        # Si el usuario ya existe o hay un error, mostrar el mensaje de error
        else: 
            print(f"Error: {respuesta.json()}\n codigo {respuesta.status_code}")
    # Si hay un error de conexión o cualquier otra excepción, mostrar el mensaje de error
    except Exception as e:
        print(f"Error al registrar el usuario: {e}")

# Función para iniciar sesión y obtener un token de autenticación
def iniciar_sesion():
    print("\n--- Iniciar Sesión ---")
    nombre = input("Nombre: ")
    contraseña = input("Contraseña: ")
    
    # Enviar una solicitud POST al servicio de usuario para iniciar sesión
    try:
        respuesta = requests.post(f"{URL_SERVICIO_USUARIO}/login", 
                                  json={"nombre": nombre, "contraseña": contraseña})
        # Si el inicio de sesión es exitoso, mostrar el mensaje de éxito
        if respuesta.status_code == 200:
            print(f"Exito: {respuesta.json()}", respuesta.status_code)
            # Devolver el token de autenticación si el inicio de sesión es exitoso
            return respuesta.json().get("token")
        # Si el usuario o la contraseña son incorrectos o hay un error, mostrar el mensaje de error
        else: 
            print(f"Error: {respuesta.json()}\n codigo {respuesta.status_code}")
            return None
    # Si hay un error de conexión o cualquier otra excepción, mostrar el mensaje de error
    except Exception as e:
        print(f"Error al iniciar sesión: {e}")
        return None

# Función para mostrar los productos disponibles en el inventario
def ver_productos(token):
    # Enviar una solicitud GET al servicio de inventario
    try:
        respuesta = requests.get(f"{URL_SERVICIO_INVENTARIO}/products", 
                                  headers={"Authorization": f"Bearer {token}"})
        # Si la solicitud es exitosa, mostrar los productos disponibles
        if respuesta.status_code == 200:
            productos = respuesta.json()
            print("\n" + "="*30)
            print("   PRODUCTOS EN INVENTARIO")
            print("="*30)
            for p in productos["Productos"]:
                print(f"ID: {p['id']} | Nombre: {p['nombre']} | Precio: ${p['precio']} | Stock: {p['stock']}")
            
            print(f"\nDesea ver un producto en detalle? (Si/No)")
            opcion = input("\nSeleccioná: ")
            if opcion.lower() == "si":
                revisar_producto(token)
            elif opcion.lower() == "no":
                pass
        # Si hay un error, mostrar el mensaje de error
        else: 
            print(f"Error: {respuesta.json()}\n codigo {respuesta.status_code}")    
    except Exception as e:
        print(f"Error al obtener los productos: {e}")

# Función para revisar los detalles de un producto específico
def revisar_producto(token):
    print("\n--- Revisar Producto ---")
    nombre_producto = input("Nombre del producto a revisar: ")
    
    # Enviar una solicitud GET al servicio de inventario para obtener el stock
    try:
        respuesta = requests.get(f"{URL_SERVICIO_INVENTARIO}/stock/{nombre_producto}", 
                                  headers={"Authorization": f"Bearer {token}"})
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            print("\n" + "="*30)
            print("   DETALLES DEL PRODUCTO")
            print("="*30)
            print(f"Producto: {datos['Producto']}")
            print(f"Stock disponible: {datos['Stock']} unidades")
            print("="*30 + "\n")
        else:
            print(f"Error: {respuesta.json()}\n codigo {respuesta.status_code}")
    except Exception as e:
        print(f"Error al revisar el producto: {e}")

# Función para agregar un nuevo producto al inventario
def agregar_producto(token):
    print("\n--- Agregar Producto ---")
    nombre = input("Nombre: ")
    precio = input("Precio: ")
    stock = input("Stock: ")
    tipo = input("Tipo de producto (ej: Ropa, Alimento): ")
    # Enviar una solicitud POST al servicio de inventario para agregar un nuevo producto
    try:
        respuesta = requests.post(f"{URL_SERVICIO_INVENTARIO}/products",
                                  json={"nombre": nombre, "precio": precio, "stock": stock, "tipo": tipo},
                                  headers={"Authorization": f"Bearer {token}"})
        # Si el producto se agrega exitosamente, mostrar el mensaje de éxito
        if respuesta.status_code >= 200 and respuesta.status_code < 300:
            print(f"Exito: {respuesta.json()}", respuesta.status_code)
        # Si hay un error, mostrar el mensaje de error
        else:
            print(f"Error: {respuesta.json()}\n codigo {respuesta.status_code}")
    except Exception as e:
        print(f"Error al agregar el producto: {e}")

def eliminar_producto(token):
    print("Este servicio no está disponible en este momento. Por favor, inténtalo más tarde.\n")
    return None

# Funcion para mostrar el menu inventario, pero solo si el usuario ha iniciado sesión correctamente
def menu_inventario(token):
    while True:
        print("\n=== Inventario ===")
        print("1. Ver productos | 2. Agregar producto | 3. Eliminar producto | 4. Volver al menú principal")
        opcion = input("\nSeleccioná: ")
        if opcion == "1": 
            ver_productos(token)
        elif opcion == "2": 
            agregar_producto(token)
        elif opcion == "3": 
            eliminar_producto(token)
        elif opcion == "4": break

    
# Función para mostrar el menú principal y manejar las opciones del usuario
def menu_principal():
    while True:
        print("\n=== Penguin Shop ===")
        print("1. Registrarse | 2. Login | 3. Salir")
        opcion = input("\nSeleccioná: ")
        if opcion == "1": 
            registrar_usuario()
        elif opcion == "2": 
            token = iniciar_sesion()
            if token:
                menu_inventario(token)
            
        elif opcion == "3": break

if __name__ == "__main__":
    menu_principal()