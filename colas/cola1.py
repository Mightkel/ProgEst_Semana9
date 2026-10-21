from collections import deque

cola = deque()
atendidos = []
def agregar(item):
    cola.append(item)
    return item

def mostrar_pendientes(cola):
    if not cola:
        return None
    return cola

def atender():
    if not cola:
        return None
    resultado = cola.popleft()
    atendidos.append(resultado)
    return resultado

def mostrar_atendidos():
    if not atendidos:
        return None
    return atendidos
