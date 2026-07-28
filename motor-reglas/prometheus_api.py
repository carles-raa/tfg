import os

import requests

PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")


def consultar_instantanea(expr):
    """Ejecuta una consulta PromQL instantánea y devuelve el primer valor numérico, o None."""
    try:
        respuesta = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": expr},
            timeout=5,
        )
        respuesta.raise_for_status()
        resultado = respuesta.json()["data"]["result"]
        if not resultado:
            return None
        return float(resultado[0]["value"][1])
    except (requests.RequestException, KeyError, ValueError, IndexError):
        return None
