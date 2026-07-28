import time

import yaml

import db
import docker_info
import reglas_engine


def cargar_config(ruta="reglas.yml"):
    with open(ruta, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def sincronizar_incidencias(conexion, señales_activas):
    """Compara las señales de esta ronda con las incidencias ya abiertas: resuelve las que
    dejaron de cumplirse y crea las nuevas. Evita crear una fila duplicada cada 30s mientras
    el problema siga activo."""
    activas_por_clave = {(s["servicio"], s["tipo"]) for s in señales_activas}

    for incidencia in db.incidencias_abiertas(conexion):
        clave = (incidencia["servicio"], incidencia["tipo_regla"])
        if clave not in activas_por_clave:
            db.resolver_incidencia(conexion, incidencia["id"])
            print(f"[RESUELTA] {incidencia['servicio']} ({incidencia['tipo_regla']})")

    abiertas_por_clave = {
        (i["servicio"], i["tipo_regla"]) for i in db.incidencias_abiertas(conexion)
    }
    for s in señales_activas:
        clave = (s["servicio"], s["tipo"])
        if clave not in abiertas_por_clave:
            db.crear_incidencia(conexion, s["servicio"], s["tipo"], s["severidad"], s["descripcion"])
            print(f"[NUEVA INCIDENCIA] {s['severidad'].upper()} - {s['servicio']}: {s['descripcion']}")


def main():
    config = cargar_config()
    intervalo = config.get("intervalo_evaluacion_segundos", 30)

    conexion = db.conectar_con_reintentos()
    db.inicializar_esquema(conexion)
    cliente_docker = docker_info.obtener_cliente()
    print("Motor de reglas conectado a MySQL y Docker.")

    while True:
        try:
            señales = reglas_engine.evaluar(conexion, cliente_docker, config)
            sincronizar_incidencias(conexion, señales)
        except Exception as error:
            print(f"Error en la ronda de evaluación: {error}")
        time.sleep(intervalo)


if __name__ == "__main__":
    main()
