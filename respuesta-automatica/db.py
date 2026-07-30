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
    """La tabla incidencias la crea motor-reglas; aquí solo añadimos la columna propia de
    este módulo, para no intentar reiniciar el mismo contenedor en cada ronda."""
    with conexion.cursor() as cursor:
        try:
            cursor.execute(
                "ALTER TABLE incidencias ADD COLUMN respuesta_intentada TINYINT(1) NOT NULL DEFAULT 0"
            )
        except pymysql.err.OperationalError as error:
            if error.args[0] != 1060:  # 1060 = Duplicate column name (ya existía)
                raise


def incidencias_pendientes_respuesta(conexion, tipos_regla):
    marcadores = ", ".join(["%s"] * len(tipos_regla))
    with conexion.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, servicio, tipo_regla, severidad, causa_probable
            FROM incidencias
            WHERE estado = 'abierta'
              AND respuesta_intentada = 0
              AND tipo_regla IN ({marcadores})
            """,
            tuple(tipos_regla),
        )
        return cursor.fetchall()


def marcar_respuesta_intentada(conexion, incidencia_id):
    with conexion.cursor() as cursor:
        cursor.execute(
            "UPDATE incidencias SET respuesta_intentada = 1 WHERE id = %s", (incidencia_id,)
        )


def ultimo_estado(conexion, nombre_check):
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT estado FROM checks_resultado
            WHERE nombre_check = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (nombre_check,),
        )
        fila = cursor.fetchone()
    return fila["estado"] if fila else None
