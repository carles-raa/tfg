import os
import time

import pymysql
import pymysql.cursors


def _config_conexion():
    return dict(
        host=os.environ.get("MYSQL_HOST", "mysql"),
        port=int(os.environ.get("MYSQL_PORT", 3306)),
        user=os.environ.get("MYSQL_USER", "monitor"),
        password=os.environ.get("MYSQL_PASSWORD", "monitor"),
        database=os.environ.get("MYSQL_DATABASE", "monitorizacion"),
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def conectar_con_reintentos(intentos=10, espera_segundos=3):
    ultimo_error = None
    for _ in range(intentos):
        try:
            return pymysql.connect(**_config_conexion())
        except pymysql.MySQLError as error:
            ultimo_error = error
            print(f"MySQL no disponible todavía, reintentando en {espera_segundos}s... ({error})")
            time.sleep(espera_segundos)
    raise ultimo_error


def inicializar_esquema(conexion):
    """La tabla incidencias la crea motor-reglas; aquí solo añadimos, si no existen ya, las
    columnas propias de este módulo para no volver a notificar algo ya notificado."""
    with conexion.cursor() as cursor:
        for columna in ("notificado_apertura", "notificado_resolucion"):
            try:
                cursor.execute(
                    f"ALTER TABLE incidencias ADD COLUMN {columna} TINYINT(1) NOT NULL DEFAULT 0"
                )
            except pymysql.err.OperationalError as error:
                if error.args[0] != 1060:  # 1060 = Duplicate column name (ya existía)
                    raise


def incidencias_pendientes_apertura(conexion):
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, servicio, tipo_regla, severidad, causa_probable, timestamp
            FROM incidencias
            WHERE notificado_apertura = 0
            """
        )
        return cursor.fetchall()


def marcar_notificado_apertura(conexion, incidencia_id):
    with conexion.cursor() as cursor:
        cursor.execute(
            "UPDATE incidencias SET notificado_apertura = 1 WHERE id = %s", (incidencia_id,)
        )


def incidencias_pendientes_resolucion(conexion):
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, servicio, tipo_regla, severidad, causa_probable, timestamp, resuelto_timestamp
            FROM incidencias
            WHERE estado = 'resuelta' AND notificado_resolucion = 0
            """
        )
        return cursor.fetchall()


def marcar_notificado_resolucion(conexion, incidencia_id):
    with conexion.cursor() as cursor:
        cursor.execute(
            "UPDATE incidencias SET notificado_resolucion = 1 WHERE id = %s", (incidencia_id,)
        )
