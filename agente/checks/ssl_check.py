import socket
import ssl
import time
from datetime import datetime, timezone

from estados import CAIDO, DEGRADADO, OK


def check_ssl(cfg):
    dominio = cfg["dominio"]
    puerto = cfg.get("puerto", 443)
    timeout = cfg.get("timeout_segundos", 5)
    umbral_dias_advertencia = cfg.get("umbral_dias_advertencia", 30)

    contexto = ssl.create_default_context()
    inicio = time.monotonic()
    try:
        with socket.create_connection((dominio, puerto), timeout=timeout) as sock:
            with contexto.wrap_socket(sock, server_hostname=dominio) as tls:
                cert = tls.getpeercert()
    except (OSError, ssl.SSLError) as error:
        return CAIDO, None, f"no se pudo comprobar el certificado de {dominio}: {error}"

    latencia_ms = (time.monotonic() - inicio) * 1000
    fecha_caducidad = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    dias_restantes = (fecha_caducidad - datetime.now(timezone.utc)).days

    if dias_restantes < 0:
        return CAIDO, latencia_ms, f"certificado caducado hace {abs(dias_restantes)} días"
    if dias_restantes < umbral_dias_advertencia:
        return DEGRADADO, latencia_ms, f"certificado caduca en {dias_restantes} días"
    return OK, latencia_ms, f"certificado válido, caduca en {dias_restantes} días"
