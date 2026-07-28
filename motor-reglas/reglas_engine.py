from datetime import datetime, timedelta, timezone

import db
import docker_info
import prometheus_api

SEVERIDAD_ORDEN = {"advertencia": 0, "critica": 1}


def _severidad_mayor(a, b):
    return a if SEVERIDAD_ORDEN.get(a, 0) >= SEVERIDAD_ORDEN.get(b, 0) else b


def evaluar(conexion, cliente_docker, config):
    """Evalúa las 7 reglas fijas y devuelve la lista de incidencias vigentes en esta ronda,
    ya consolidadas (una por causa, no una por regla individual)."""
    señales = []

    # Regla 1: servicio caído N comprobaciones consecutivas -> crítica.
    for nombre_check, num in config.get("caida_consecutiva", {}).items():
        estados = db.ultimos_estados(conexion, nombre_check, num)
        if len(estados) == num and all(e == "CAIDO" for e in estados):
            señales.append({
                "servicio": nombre_check,
                "tipo": "caida_consecutiva",
                "severidad": "critica",
                "descripcion": f"{nombre_check} lleva {num} comprobaciones seguidas en CAÍDO",
            })

    # Regla 2: certificado SSL caduca en menos de X días -> advertencia.
    umbral_ssl = config["umbral_dias_ssl_advertencia"]
    for nombre_check in config.get("checks_ssl", []):
        fila = db.ultimo_resultado(conexion, nombre_check)
        if fila and fila["valor_extra"] is not None and fila["valor_extra"] < umbral_ssl:
            señales.append({
                "servicio": nombre_check,
                "tipo": "ssl_proximo_caducar",
                "severidad": "advertencia",
                "descripcion": f"certificado de {nombre_check} caduca en {fila['valor_extra']:.0f} días",
            })

    # Regla 3: latencia media por encima del umbral durante una ventana -> advertencia.
    ventana_latencia = config["ventana_latencia_minutos"]
    for nombre_check, umbral_ms in config.get("umbral_latencia_ms", {}).items():
        media = db.latencia_media(conexion, nombre_check, ventana_latencia)
        if media is not None and media > umbral_ms:
            señales.append({
                "servicio": nombre_check,
                "tipo": "latencia_alta",
                "severidad": "advertencia",
                "descripcion": f"latencia media de {nombre_check} en {media:.0f}ms "
                                f"(umbral {umbral_ms}ms, últimos {ventana_latencia} min)",
            })

    # Regla 4: contenedor reiniciado más de X veces en una ventana -> crítica.
    ventana_reinicios = config["ventana_reinicios_minutos"]
    umbral_reinicios = config["umbral_reinicios"]
    for contenedor in config.get("contenedores_vigilados", []):
        restart_count = docker_info.obtener_restart_count(cliente_docker, contenedor)
        if restart_count is not None:
            db.registrar_estado_contenedor(conexion, contenedor, restart_count)

        delta = db.restart_count_delta(conexion, contenedor, ventana_reinicios)
        if delta is not None and delta > umbral_reinicios:
            señales.append({
                "servicio": contenedor,
                "tipo": "reinicio_frecuente",
                "severidad": "critica",
                "descripcion": f"{contenedor} se reinició {delta} veces en {ventana_reinicios} min",
            })

    # Señal para la regla 5: % de pings fallidos recientes (se combina con latencia_alta).
    num_checks_perdida = config["ventana_perdida_paquetes_num_checks"]
    umbral_perdida_pct = config["umbral_perdida_paquetes_pct"]
    for nombre_check in config.get("checks_ping_perdida", []):
        estados = db.ultimos_estados(conexion, nombre_check, num_checks_perdida)
        if estados:
            pct_caido = 100 * estados.count("CAIDO") / len(estados)
            if pct_caido >= umbral_perdida_pct:
                señales.append({
                    "servicio": nombre_check,
                    "tipo": "perdida_paquetes",
                    "severidad": "advertencia",
                    "descripcion": f"{pct_caido:.0f}% de los últimos {len(estados)} pings a "
                                    f"{nombre_check} fallaron",
                })

    # Señal para la regla 6: último check HTTP con código 5xx (se combina con cpu_alta).
    for nombre_check in config.get("checks_http_5xx", []):
        fila = db.ultimo_resultado(conexion, nombre_check)
        if fila and fila["valor_extra"] is not None and 500 <= fila["valor_extra"] < 600:
            señales.append({
                "servicio": nombre_check,
                "tipo": "error_5xx",
                "severidad": "advertencia",
                "descripcion": f"{nombre_check} devuelve código {fila['valor_extra']:.0f}",
            })

    cpu_pct = prometheus_api.consultar_instantanea(
        '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
    )
    if cpu_pct is not None and cpu_pct > config["umbral_cpu_alta_pct"]:
        señales.append({
            "servicio": "sistema",
            "tipo": "cpu_alta",
            "severidad": "advertencia",
            "descripcion": f"CPU del sistema al {cpu_pct:.0f}%",
        })

    # Regla 7: patrones de error recurrentes en los logs de los contenedores vigilados.
    ventana_log = config["ventana_log_minutos"]
    umbral_ocurrencias = config["umbral_ocurrencias_log"]
    desde = datetime.now(timezone.utc) - timedelta(minutes=ventana_log)
    patrones_cfg = config.get("patrones_log", [])
    for contenedor in config.get("contenedores_vigilados", []):
        conteos = docker_info.contar_patrones_log(
            cliente_docker, contenedor, [p["patron"] for p in patrones_cfg], desde
        )
        for patron_cfg in patrones_cfg:
            conteo = conteos.get(patron_cfg["patron"], 0)
            if conteo >= umbral_ocurrencias:
                señales.append({
                    "servicio": contenedor,
                    "tipo": "logs_erroneos",
                    "severidad": patron_cfg["severidad"],
                    "descripcion": f"{conteo} apariciones de '{patron_cfg['patron']}' en logs de "
                                    f"{contenedor} en los últimos {ventana_log} min",
                })

    return _correlacionar(señales, config.get("correlaciones", []))


def _correlacionar(señales, correlaciones):
    """Si varias señales de tipos relacionados aparecen en la misma ronda, las fusiona en
    una única incidencia con causa probable combinada, en vez de generar una por señal."""
    tipos_presentes = {s["tipo"] for s in señales}
    consumidos = set()
    resultado = []

    for correlacion in correlaciones:
        tipos_necesarios = set(correlacion["combina"])
        if tipos_necesarios.issubset(tipos_presentes):
            implicadas = [s for s in señales if s["tipo"] in tipos_necesarios]
            severidad = correlacion.get("severidad", "advertencia")
            for s in implicadas:
                severidad = _severidad_mayor(severidad, s["severidad"])

            resultado.append({
                "servicio": implicadas[0]["servicio"],
                "tipo": correlacion["nombre"],
                "severidad": severidad,
                "descripcion": correlacion["causa_probable"] + ": "
                               + "; ".join(s["descripcion"] for s in implicadas),
            })
            consumidos.update(s["tipo"] for s in implicadas)

    for s in señales:
        if s["tipo"] not in consumidos:
            resultado.append(s)

    return resultado
