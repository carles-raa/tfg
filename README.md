# Plataforma de alerta temprana y respuesta automática

TFG de Ingeniería Telemática: plataforma de monitorización que detecta caídas y degradaciones
progresivas de servicios (latencia alta, errores intermitentes, certificados a punto de caducar,
saturación de recursos), correlaciona eventos relacionados en una sola alerta con causa probable,
y ejecuta una respuesta automática básica (reinicio de contenedor + notificación).

## Estado del proyecto

En construcción. Ver `docs/GLOSARIO_DEFENSA.md` para las decisiones de diseño tomadas hasta ahora.

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

Para pararlo todo: `docker compose down` (añade `-v` solo si quieres borrar también los datos guardados).

## Próximos pasos

Ver `MEGA_PROMPT_TFG.md` para el plan completo por fases.
