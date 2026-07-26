from prometheus_client import Gauge, start_http_server

ESTADO_NUMERICO = {"OK": 0, "DEGRADADO": 1, "CAIDO": 2}

check_estado = Gauge(
    "agente_check_estado",
    "Estado del check: 0=OK, 1=DEGRADADO, 2=CAIDO",
    ["nombre_check", "tipo"],
)

check_latencia_ms = Gauge(
    "agente_check_latencia_ms",
    "Latencia del check en milisegundos",
    ["nombre_check", "tipo"],
)


def iniciar_servidor_metricas(puerto=9101):
    start_http_server(puerto)


def actualizar_metricas(nombre_check, tipo, estado, latencia_ms):
    check_estado.labels(nombre_check=nombre_check, tipo=tipo).set(ESTADO_NUMERICO[estado])
    if latencia_ms is not None:
        check_latencia_ms.labels(nombre_check=nombre_check, tipo=tipo).set(latencia_ms)
