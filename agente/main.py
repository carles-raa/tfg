import time

import yaml

import db
import metrics
from checks.dns_check import check_dns
from checks.http_check import check_http
from checks.ping_check import check_ping
from checks.ssl_check import check_ssl
from checks.tcp_check import check_tcp

CHEQUEADORES = {
    "http": check_http,
    "tcp": check_tcp,
    "dns": check_dns,
    "ssl": check_ssl,
    "ping": check_ping,
}


def cargar_config(ruta="config.yml"):
    with open(ruta, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ejecutar_ronda(conexion, checks):
    for check_cfg in checks:
        nombre = check_cfg["nombre"]
        tipo = check_cfg["tipo"]
        chequeador = CHEQUEADORES.get(tipo)
        if chequeador is None:
            print(f"[{nombre}] tipo de check desconocido: {tipo}")
            continue

        try:
            estado, latencia_ms, detalle = chequeador(check_cfg)
        except Exception as error:
            estado, latencia_ms, detalle = "CAIDO", None, f"error inesperado: {error}"

        print(f"[{nombre}] {estado} - {detalle}")
        db.guardar_resultado(conexion, nombre, tipo, estado, latencia_ms, detalle)
        metrics.actualizar_metricas(nombre, tipo, estado, latencia_ms)


def main():
    config = cargar_config()
    intervalo = config.get("intervalo_global_segundos", 30)

    metrics.iniciar_servidor_metricas(9101)
    print("Servidor de métricas escuchando en :9101/metrics")

    conexion = db.conectar_con_reintentos()
    db.inicializar_esquema(conexion)
    print("Conectado a MySQL y esquema listo.")

    while True:
        ejecutar_ronda(conexion, config["checks"])
        time.sleep(intervalo)


if __name__ == "__main__":
    main()
