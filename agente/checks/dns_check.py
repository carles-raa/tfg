import socket
import time

from estados import CAIDO, DEGRADADO, OK


def check_dns(cfg):
    dominio = cfg["dominio"]
    timeout = cfg.get("timeout_segundos", 3)
    umbral_degradado = cfg.get("umbral_resolucion_degradado_ms", 200)

    socket.setdefaulttimeout(timeout)
    inicio = time.monotonic()
    try:
        ip = socket.gethostbyname(dominio)
    except socket.error as error:
        return CAIDO, None, f"no se pudo resolver {dominio}: {error}"
    finally:
        socket.setdefaulttimeout(None)

    latencia_ms = (time.monotonic() - inicio) * 1000
    if latencia_ms >= umbral_degradado:
        return DEGRADADO, latencia_ms, f"resolución lenta ({latencia_ms:.0f}ms) -> {ip}"
    return OK, latencia_ms, f"resuelto a {ip} en {latencia_ms:.0f}ms"
