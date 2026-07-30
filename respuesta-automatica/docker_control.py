import docker


def obtener_cliente():
    return docker.from_env()


def reiniciar_contenedor(cliente, nombre_contenedor):
    """Devuelve True si se pudo lanzar el reinicio, False si el contenedor no existe."""
    try:
        contenedor = cliente.containers.get(nombre_contenedor)
    except docker.errors.NotFound:
        return False

    contenedor.restart()
    return True
