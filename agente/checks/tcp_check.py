import socket
import time

from estados import CAIDO, DEGRADADO, OK


def check_tcp(cfg):
    host = cfg["host"]
    puerto = cfg["puerto"]
    timeout = cfg.get("timeout_segundos", 3)
    umbral_degradado = cfg.get("umbral_latencia_degradado_ms", 200)

    inicio = time.monotonic()
    try:
        with socket.create_connection((host, puerto), timeout=timeout):
            pass
    except OSError as error:
        return CAIDO, None, f"no se pudo conectar a {host}:{puerto}: {error}", None

    latencia_ms = (time.monotonic() - inicio) * 1000
    if latencia_ms >= umbral_degradado:
        return DEGRADADO, latencia_ms, f"conexión lenta: {latencia_ms:.0f}ms", None
    return OK, latencia_ms, f"conexión OK en {latencia_ms:.0f}ms", None
