import requests, os, json

MODO_DOCKER = os.environ.get("DOCKER_ENV")
URL_SERVICIO_USUARIO = "http://servicio-user:5000"  if MODO_DOCKER else "http://localhost:5000"


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
    
    
def menu_principal():
    while True:
        print("\n=== Penguin Shop ===")
        print("1. Registrarse | 2. Login | 3. Salir")
        opcion = input("\nSeleccioná: ")
        if opcion == "1": registrar_usuario()
        elif opcion == "2": iniciar_sesion()
        elif opcion == "3": break

if __name__ == "__main__":
    menu_principal()