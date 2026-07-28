# Plataforma de alerta temprana y respuesta automática

TFG de Ingeniería Telemática: plataforma de monitorización que detecta caídas y degradaciones
progresivas de servicios (latencia alta, errores intermitentes, certificados a punto de caducar,
saturación de recursos), correlaciona eventos relacionados en una sola alerta con causa probable,
y ejecuta una respuesta automática básica (reinicio de contenedor + notificación).

Ver `docs/GLOSARIO_DEFENSA.md` para las decisiones de diseño tomadas hasta ahora.

## Arranque de la infraestructura base

Requisitos: Docker y Docker Compose instalados.

```bash
docker compose up -d
```

Esto levanta:

| Servicio      | Puerto local | Qué es |
|---------------|--------------|--------|
| MySQL         | 3306         | Base de datos de incidencias |
| Prometheus    | 9090         | Recolector de métricas |
| Grafana       | 3000         | Panel de dashboards (usuario/contraseña: admin/admin) |
| Node Exporter | 9100         | Métricas del sistema (CPU, memoria, disco) |
| cAdvisor      | 8080         | Métricas de contenedores Docker |
| demo-web      | 8081         | Servicio web de prueba (nginx) para simular incidentes |
| Agente        | 9101         | Métricas del agente de monitorización (`/metrics`) |

Para pararlo todo: `docker compose down` (añade `-v` solo si quieres borrar también los datos guardados).

## Estado del proyecto

**Fase 1 completada:** agente de monitorización activa (`agente/`). Comprueba cada 30s (configurable
en `agente/config.yml`) el estado de los servicios definidos mediante 5 tipos de check: HTTP, TCP,
DNS, certificado SSL y ping. Cada check se clasifica como `OK`, `DEGRADADO` o `CAÍDO`, se guarda en
MySQL (tabla `checks_resultado`) y se expone como métrica Prometheus en `http://localhost:9101/metrics`.

Evidencia de que detecta caídas reales en `docs/fase1_evidencia_caida_demo-web.md`.

Para ver los checks en vivo:
```bash
curl http://localhost:9101/metrics | grep agente_check
```

Para ver los resultados guardados en MySQL:
```bash
docker compose exec mysql mysql --default-character-set=utf8mb4 -u monitor -pmonitor monitorizacion \
  -e "SELECT * FROM checks_resultado ORDER BY id DESC LIMIT 10;"
```

**Fase 2 completada:** dashboard de Grafana provisionado automáticamente (`infra/grafana/dashboards/`)
con estado de checks, CPU/memoria del sistema y CPU/memoria por contenedor. Motor de reglas
(`motor-reglas/`) que cada 30s evalúa 7 reglas fijas (definidas en `motor-reglas/reglas.yml`,
no en código): caída consecutiva, certificado SSL próximo a caducar, latencia media alta,
reinicios frecuentes de contenedor, pérdida de paquetes + latencia (correlacionadas), errores
5xx + CPU alta (correlacionadas), y patrones de error recurrentes en logs. Guarda cada incidencia
en MySQL (tabla `incidencias`) y la resuelve automáticamente cuando la condición desaparece.

Evidencia en `docs/fase2_evidencia_motor_reglas.md`.

Dashboard: `http://localhost:3000` (admin/admin) → "TFG - Monitorización de servicios".

Para ver las incidencias abiertas:
```bash
docker compose exec mysql mysql --default-character-set=utf8mb4 -u monitor -pmonitor monitorizacion \
  -e "SELECT * FROM incidencias WHERE estado='abierta';"
```

## Próximos pasos

Ver `MEGA_PROMPT_TFG.md` para el plan completo por fases. Siguiente: Fase 3 (notificaciones por
Telegram, respuesta automática y panel FastAPI).
