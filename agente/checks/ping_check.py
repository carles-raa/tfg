from ping3 import ping

from estados import CAIDO, DEGRADADO, OK


def check_ping(cfg):
    host = cfg["host"]
    timeout = cfg.get("timeout_segundos", 3)
    umbral_degradado = cfg.get("umbral_latencia_degradado_ms", 100)

    try:
        latencia_seg = ping(host, timeout=timeout, unit="s")
    except Exception as error:
        return CAIDO, None, f"error al hacer ping a {host}: {error}", None

    if latencia_seg is None or latencia_seg is False:
        return CAIDO, None, f"{host} no responde al ping", None

    latencia_ms = latencia_seg * 1000
    if latencia_ms >= umbral_degradado:
        return DEGRADADO, latencia_ms, f"latencia alta: {latencia_ms:.0f}ms", None
    return OK, latencia_ms, f"ping OK en {latencia_ms:.0f}ms", None
