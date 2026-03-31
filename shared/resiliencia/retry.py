import time 
import functools

# Funciones para configurar la estrategia de retry
def parar_despues_de_intentos(max_intentos):
    return max_intentos


def esperar_exponencialmente(base):
    
    return base

# Decorador de retry
def retry(parar, esperar):
    # Función decoradora que envuelve la función original con la lógica de retry
    def decorador(funcion):
        @functools.wraps(funcion) # Mantener la firma de la función original
        def wrapper(*args, **kwargs): # Lógica de retry
            intentos = 0
            
            # Bucle de retry
            while intentos < parar:
                try:
                    return funcion(*args, **kwargs)
                except Exception as e:
                    intentos += 1
                    if intentos >= parar:
                        raise e
                    # Exponential Back off
                    tiempo_espera = esperar * (2 ** (intentos - 1))
                    print(f"Reintentando en {tiempo_espera} segundos... \nPor favor espere, Reintento {intentos}\{parar} en {tiempo_espera} segundos")
                    time.sleep(tiempo_espera)
        return wrapper
    return decorador