import docker


def obtener_cliente():
    return docker.from_env()


def obtener_restart_count(cliente, nombre_contenedor):
    """Nº de veces que la política de reinicio de Docker ha reiniciado el contenedor."""
    try:
        contenedor = cliente.containers.get(nombre_contenedor)
        return contenedor.attrs["RestartCount"]
    except docker.errors.NotFound:
        return None


def contar_patrones_log(cliente, nombre_contenedor, patrones, desde):
    """Cuenta cuántas veces aparece cada patrón en los logs del contenedor desde `desde`."""
    try:
        contenedor = cliente.containers.get(nombre_contenedor)
        crudo = contenedor.logs(since=desde, timestamps=False).decode("utf-8", errors="ignore")
    except docker.errors.NotFound:
        return {patron: 0 for patron in patrones}

    texto = crudo.lower()
    return {patron: texto.count(patron.lower()) for patron in patrones}
