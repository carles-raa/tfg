import os
import time

import pymysql


def _config_conexion():
    return dict(
        host=os.environ.get("MYSQL_HOST", "mysql"),
        port=int(os.environ.get("MYSQL_PORT", 3306)),
        user=os.environ.get("MYSQL_USER", "monitor"),
        password=os.environ.get("MYSQL_PASSWORD", "monitor"),
        database=os.environ.get("MYSQL_DATABASE", "monitorizacion"),
        charset="utf8mb4",
        autocommit=True,
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
            CREATE TABLE IF NOT EXISTS checks_resultado (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre_check VARCHAR(100) NOT NULL,
                tipo VARCHAR(20) NOT NULL,
                estado VARCHAR(20) NOT NULL,
                latencia_ms FLOAT,
                detalle TEXT,
                valor_extra FLOAT,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        try:
            cursor.execute("ALTER TABLE checks_resultado ADD COLUMN valor_extra FLOAT")
        except pymysql.err.OperationalError as error:
            if error.args[0] != 1060:  # 1060 = Duplicate column name (ya existía)
                raise


def guardar_resultado(conexion, nombre_check, tipo, estado, latencia_ms, detalle, valor_extra=None):
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO checks_resultado (nombre_check, tipo, estado, latencia_ms, detalle, valor_extra)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (nombre_check, tipo, estado, latencia_ms, detalle, valor_extra),
        )
