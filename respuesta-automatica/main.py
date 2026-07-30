import time

import yaml

import db
import docker_control
import telegram


def cargar_config(ruta="config.yml"):
    with open(ruta, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def atender_incidencia(conexion, cliente_docker, config, incidencia, contenedores_ya_reiniciados):
    db.marcar_respuesta_intentada(conexion, incidencia["id"])

    contenedor = config["contenedor_por_servicio"].get(incidencia["servicio"])
    if contenedor is None:
        print(f"[{incidencia['servicio']}] no hay contenedor asociado en config.yml, no se actúa")
        return

    if contenedor in contenedores_ya_reiniciados:
        # Otra incidencia de esta misma ronda ya reinició este contenedor (ej. los checks HTTP
        # y TCP del mismo servicio cayeron a la vez): no lo reiniciamos dos veces seguidas.
        print(f"[{incidencia['servicio']}] {contenedor} ya se reinició en esta ronda, no se repite")
        return
    contenedores_ya_reiniciados.add(contenedor)

    print(f"[{incidencia['servicio']}] intentando reiniciar contenedor {contenedor}...")
    telegram.enviar_mensaje(
        f"🔧 *Respuesta automática*\nReiniciando contenedor `{contenedor}` por incidencia en "
        f"{incidencia['servicio']} ({incidencia['causa_probable']})"
    )

    reiniciado = docker_control.reiniciar_contenedor(cliente_docker, contenedor)
    if not reiniciado:
        telegram.enviar_mensaje(
            f"⚠️ *Requiere intervención manual*\nNo se encontró el contenedor `{contenedor}` "
            f"para reiniciarlo (servicio {incidencia['servicio']})."
        )
        return

    espera = config["espera_tras_reinicio_segundos"]
    time.sleep(espera)

    estado_tras_reinicio = db.ultimo_estado(conexion, incidencia["servicio"])
    if estado_tras_reinicio == "OK":
        print(f"[{incidencia['servicio']}] recuperado tras el reinicio")
        telegram.enviar_mensaje(
            f"✅ *Recuperado tras reinicio automático*\nServicio: {incidencia['servicio']}"
        )
    else:
        print(f"[{incidencia['servicio']}] sigue sin responder tras el reinicio ({estado_tras_reinicio})")
        telegram.enviar_mensaje(
            f"⚠️ *Requiere intervención manual*\nEl reinicio automático de `{contenedor}` no "
            f"resolvió el problema en {incidencia['servicio']} (estado tras {espera}s: "
            f"{estado_tras_reinicio})."
        )


def main():
    config = cargar_config()
    intervalo = config.get("intervalo_segundos", 15)

    conexion = db.conectar_con_reintentos()
    db.inicializar_esquema(conexion)
    cliente_docker = docker_control.obtener_cliente()
    print("Respuesta automática conectada a MySQL y Docker.")

    while True:
        try:
            pendientes = db.incidencias_pendientes_respuesta(
                conexion, config["tipos_regla_que_disparan_reinicio"]
            )
            contenedores_ya_reiniciados = set()
            for incidencia in pendientes:
                atender_incidencia(conexion, cliente_docker, config, incidencia, contenedores_ya_reiniciados)
        except Exception as error:
            print(f"Error en la ronda de respuesta automática: {error}")
        time.sleep(intervalo)


if __name__ == "__main__":
    main()
