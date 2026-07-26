import time

import requests

from estados import CAIDO, DEGRADADO, OK


def check_http(cfg):
    target = cfg["target"]
    timeout = cfg.get("timeout_segundos", 3)
    codigo_esperado = cfg.get("codigo_esperado", 200)
    umbral_degradado = cfg.get("umbral_latencia_degradado_ms", 300)
    umbral_caido = cfg.get("umbral_latencia_caido_ms", 3000)

    inicio = time.monotonic()
    try:
        respuesta = requests.get(target, timeout=timeout)
    except requests.RequestException as error:
        return CAIDO, None, f"error de conexión: {error}"

    latencia_ms = (time.monotonic() - inicio) * 1000

    if respuesta.status_code != codigo_esperado:
        return CAIDO, latencia_ms, f"código {respuesta.status_code}, se esperaba {codigo_esperado}"
    if latencia_ms >= umbral_caido:
        return CAIDO, latencia_ms, f"latencia {latencia_ms:.0f}ms >= umbral caído {umbral_caido}ms"
    if latencia_ms >= umbral_degradado:
        return DEGRADADO, latencia_ms, f"latencia {latencia_ms:.0f}ms >= umbral degradado {umbral_degradado}ms"
    return OK, latencia_ms, f"código {respuesta.status_code}, latencia {latencia_ms:.0f}ms"
