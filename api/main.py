from datetime import timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

import db

app = FastAPI(
    title="Panel de incidencias — TFG monitorización",
    description="API de solo consulta sobre las incidencias detectadas por el motor de reglas. "
                "Pensada para enseñarse con curl o con la Swagger UI (/docs) durante la defensa.",
)


@app.get("/incidencias")
def listar_incidencias(
    severidad: Optional[str] = Query(None, description="critica, advertencia o informativa"),
    estado: Optional[str] = Query(None, description="abierta o resuelta"),
):
    return db.listar_incidencias(severidad=severidad, estado=estado)


@app.get("/incidencias/{incidencia_id}")
def obtener_incidencia(incidencia_id: int):
    incidencia = db.obtener_incidencia(incidencia_id)
    if incidencia is None:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    return incidencia


@app.get("/incidencias/{incidencia_id}/informe", response_class=PlainTextResponse)
def informe_incidencia(incidencia_id: int):
    """Informe básico post-incidente en texto plano: causa, duración y checks que la dispararon."""
    incidencia = db.obtener_incidencia(incidencia_id)
    if incidencia is None:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    inicio = incidencia["timestamp"]
    fin = incidencia["resuelto_timestamp"] or incidencia["timestamp"]
    ventana_desde = inicio - timedelta(minutes=5)
    ventana_hasta = fin + timedelta(minutes=5)

    checks = db.checks_relacionados(incidencia["servicio"], ventana_desde, ventana_hasta)

    duracion = "incidencia todavía abierta"
    if incidencia["resuelto_timestamp"]:
        segundos = (incidencia["resuelto_timestamp"] - incidencia["timestamp"]).total_seconds()
        duracion = f"{segundos:.0f} segundos"

    lineas = [
        f"INFORME DE INCIDENCIA #{incidencia['id']}",
        "=" * 40,
        f"Servicio afectado: {incidencia['servicio']}",
        f"Severidad: {incidencia['severidad']}",
        f"Causa probable: {incidencia['causa_probable']}",
        f"Abierta: {incidencia['timestamp']}",
        f"Resuelta: {incidencia['resuelto_timestamp'] or '(sigue abierta)'}",
        f"Duración: {duracion}",
        f"Estado actual: {incidencia['estado']}",
        "",
        "Checks relacionados en la ventana del incidente:",
    ]

    if checks:
        for check in checks:
            lineas.append(
                f"  - {check['timestamp']} | {check['nombre_check']} ({check['tipo']}): "
                f"{check['estado']} — {check['detalle']}"
            )
    else:
        lineas.append("  (sin checks registrados en esa ventana)")

    return "\n".join(lineas)
