import time
import functools

# 
class CircuitBreaker:
    def __init__(self, max_fallas= 5, tiempo_reset = 10, nombre = "CircuitBreaker"):
        self.max_fallas = max_fallas
        self.tiempo_reset = tiempo_reset
        self.nombre = nombre
        self.fallas = 0
        self.estado = "CERRADO" # CERRADO (flujo normal), ABIERTO (bloqueado)
        self.ultimo_fallo = None
        
    def __call__(self, funcion):
        @functools.wraps(funcion)
        def wrapper(*args, **kwargs):
            if self.estado == "ABIERTO":
                # Si ya paso el tiempo de reset, cambiar a SEMICERRADO
                if time.time() - self.ultimo_fallo >= self.tiempo_reset:
                    print(f"{self.nombre} Tiempo de reset completo, Probando servicio")
                    self.estado = "CERRADO"
                else:
                    raise Exception(f"Circuito{self.nombre} Circuito abierto. Peticion abortada")
                
            try:
                resultado = funcion(*args, **kwargs)
                self.fallas = 0 # Reiniciar el contador de fallas si la funcion se ejecuta correctamente
                return resultado
            
            except Exception as e:
                self.fallas += 1
                self.ultimo_fallo = time.time()
                print(f"{self.nombre} Error detectado ({self.fallas}/{self.max_fallas})")
                
                if self.fallas >= self.max_fallas:
                    self.estado = "ABIERTO"
                    print(f"{self.nombre} Circuito abierto")
                raise e
        return wrapper
        
                    