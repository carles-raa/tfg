import os

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


def conectar():
    return pymysql.connect(**_config_conexion())


def listar_incidencias(severidad=None, estado=None):
    condiciones = []
    valores = []
    if severidad:
        condiciones.append("severidad = %s")
        valores.append(severidad)
    if estado:
        condiciones.append("estado = %s")
        valores.append(estado)

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    conexion = conectar()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, servicio, tipo_regla, severidad, causa_probable, timestamp,
                       resuelto_timestamp, estado
                FROM incidencias
                {where}
                ORDER BY id DESC
                """,
                tuple(valores),
            )
            return cursor.fetchall()
    finally:
        conexion.close()


def obtener_incidencia(incidencia_id):
    conexion = conectar()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, servicio, tipo_regla, severidad, causa_probable, timestamp,
                       resuelto_timestamp, estado
                FROM incidencias
                WHERE id = %s
                """,
                (incidencia_id,),
            )
            return cursor.fetchone()
    finally:
        conexion.close()


def checks_relacionados(servicio, desde, hasta):
    conexion = conectar()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT nombre_check, tipo, estado, latencia_ms, detalle, valor_extra, timestamp
                FROM checks_resultado
                WHERE nombre_check = %s
                  AND timestamp BETWEEN %s AND %s
                ORDER BY timestamp ASC
                """,
                (servicio, desde, hasta),
            )
            return cursor.fetchall()
    finally:
        conexion.close()
