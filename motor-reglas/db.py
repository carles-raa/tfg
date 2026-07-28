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
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS incidencias (
                id INT AUTO_INCREMENT PRIMARY KEY,
                servicio VARCHAR(100) NOT NULL,
                tipo_regla VARCHAR(50) NOT NULL,
                severidad VARCHAR(20) NOT NULL,
                causa_probable TEXT NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resuelto_timestamp DATETIME NULL,
                estado VARCHAR(20) NOT NULL DEFAULT 'abierta'
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS contenedor_estado (
                id INT AUTO_INCREMENT PRIMARY KEY,
                contenedor VARCHAR(100) NOT NULL,
                restart_count INT NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def ultimos_estados(conexion, nombre_check, cantidad):
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT estado FROM checks_resultado
            WHERE nombre_check = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (nombre_check, cantidad),
        )
        filas = cursor.fetchall()
    return [fila["estado"] for fila in filas]


def ultimo_resultado(conexion, nombre_check):
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT estado, latencia_ms, valor_extra FROM checks_resultado
            WHERE nombre_check = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (nombre_check,),
        )
        return cursor.fetchone()


def latencia_media(conexion, nombre_check, ventana_minutos):
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT AVG(latencia_ms) AS media FROM checks_resultado
            WHERE nombre_check = %s
              AND latencia_ms IS NOT NULL
              AND timestamp >= NOW() - INTERVAL %s MINUTE
            """,
            (nombre_check, ventana_minutos),
        )
        fila = cursor.fetchone()
    return fila["media"] if fila and fila["media"] is not None else None


def registrar_estado_contenedor(conexion, contenedor, restart_count):
    with conexion.cursor() as cursor:
        cursor.execute(
            "INSERT INTO contenedor_estado (contenedor, restart_count) VALUES (%s, %s)",
            (contenedor, restart_count),
        )


def restart_count_delta(conexion, contenedor, ventana_minutos):
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT MAX(restart_count) - MIN(restart_count) AS delta FROM contenedor_estado
            WHERE contenedor = %s
              AND timestamp >= NOW() - INTERVAL %s MINUTE
            """,
            (contenedor, ventana_minutos),
        )
        fila = cursor.fetchone()
    return fila["delta"] if fila and fila["delta"] is not None else None


def incidencias_abiertas(conexion):
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT id, servicio, tipo_regla, severidad, causa_probable "
            "FROM incidencias WHERE estado = 'abierta'"
        )
        return cursor.fetchall()


def crear_incidencia(conexion, servicio, tipo_regla, severidad, causa_probable):
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO incidencias (servicio, tipo_regla, severidad, causa_probable)
            VALUES (%s, %s, %s, %s)
            """,
            (servicio, tipo_regla, severidad, causa_probable),
        )


def resolver_incidencia(conexion, incidencia_id):
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            UPDATE incidencias
            SET estado = 'resuelta', resuelto_timestamp = NOW()
            WHERE id = %s
            """,
            (incidencia_id,),
        )
