import time

import db
import telegram

INTERVALO_SEGUNDOS = 10

SEVERIDAD_EMOJI = {"critica": "🔴", "advertencia": "🟠", "informativa": "🔵"}


def formatear_apertura(incidencia):
    emoji = SEVERIDAD_EMOJI.get(incidencia["severidad"], "⚪")
    return (
        f"{emoji} *Nueva incidencia* ({incidencia['severidad'].upper()})\n"
        f"Servicio: {incidencia['servicio']}\n"
        f"Causa probable: {incidencia['causa_probable']}\n"
        f"Hora: {incidencia['timestamp']}"
    )


def formatear_resolucion(incidencia):
    return (
        f"✅ *Incidencia resuelta*\n"
        f"Servicio: {incidencia['servicio']}\n"
        f"Causa probable: {incidencia['causa_probable']}\n"
        f"Resuelta: {incidencia['resuelto_timestamp']}"
    )


def main():
    conexion = db.conectar_con_reintentos()
    db.inicializar_esquema(conexion)
    print("Servicio de notificaciones conectado a MySQL.")

    while True:
        for incidencia in db.incidencias_pendientes_apertura(conexion):
            telegram.enviar_mensaje(formatear_apertura(incidencia))
            db.marcar_notificado_apertura(conexion, incidencia["id"])

        for incidencia in db.incidencias_pendientes_resolucion(conexion):
            telegram.enviar_mensaje(formatear_resolucion(incidencia))
            db.marcar_notificado_resolucion(conexion, incidencia["id"])

        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    main()
