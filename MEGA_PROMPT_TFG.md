# Prompt maestro — TFG: Plataforma de alerta temprana y respuesta automática

## Contexto para ti (Claude Code)

Vas a construir de principio a fin un Trabajo de Fin de Grado de Ingeniería Telemática.

- Explica cada paso que des en lenguaje sencillo, sin jerga sin explicar, antes de ejecutar comandos.
- Después de cada bloque de trabajo (no después de cada línea), resume en 2-3 frases qué has hecho y por qué,
  como si se lo explicaras a alguien que va a tener que defender esto oralmente ante un tribunal
  pero que nunca ha programado.
- Si tomas una decisión de diseño (ej. "uso este umbral", "elijo esta librería"), dilo explícitamente
  y por qué, en una frase — esas frases son las que él va a memorizar para la defensa.
- No asumas que sabe qué es un contenedor, un endpoint, una variable de entorno, etc. — una frase de
  contexto la primera vez que aparezca cada concepto es suficiente, no hace falta un curso.
- Ve construyendo un archivo `docs/GLOSARIO_DEFENSA.md` con una entrada por cada concepto/decisión clave,
  en formato: **Concepto/decisión** → explicación en 2-3 frases en español sencillo. Esto es lo que él
  va a estudiar antes de la defensa.

## Repositorio

- Remoto: `https://github.com/carles-raa/tfg.git`
- Haz commits pequeños y frecuentes, con mensajes claros en español (ej. `feat: agente de checks HTTP y TCP`).
- Push a `main` tras cada hito funcional (fin de cada fase).

## Objetivo del proyecto

Plataforma de monitorización inteligente que detecta no solo caídas de servicios, sino degradaciones
progresivas (latencia alta, errores intermitentes, certificados a punto de caducar, saturación de
recursos), correlaciona eventos relacionados en una sola alerta con causa probable, y ejecuta una
respuesta automática básica (reinicio de contenedor + notificación).

**Alcance cerrado para 3 semanas — NO os salgáis de esto sin confirmar conmigo:**
- Motor de correlación: reglas expertas fijas (NO machine learning, NO LLM como pieza funcional).
- Panel de visualización: Grafana (NO frontend custom).
- Respuesta automática: solo reinicio de contenedor Docker + notificación de recuperación/fallo.
- Base de datos de incidencias: MySQL.

## Stack técnico (ya decidido)

- Python 3.11+ con `venv` + `requirements.txt` (nada de poetry, mantenlo simple).
- FastAPI para la API interna de la plataforma (panel de incidencias/estado).
- MySQL para la base de datos de incidencias.
- Prometheus + Node Exporter + cAdvisor para métricas.
- Grafana para dashboards.
- Docker Compose para orquestar todo.
- Telegram Bot API para notificaciones.
- Docker SDK para Python (`docker-py`) para la respuesta automática.

## Estructura de carpetas (ya creada, respétala)

```
tfg-monitorizacion/
├── agente/                  # Módulo 1: monitorización activa
├── motor-reglas/             # Módulo 3: correlación, severidad y análisis de logs
├── notificaciones/           # Telegram, email
├── respuesta-automatica/     # Módulo 4: acciones correctivas
├── infra/
│   ├── prometheus/
│   ├── grafana/
│   └── servicios-demo/       # web/API/BD dummy para simular incidentes
├── docs/                     # capturas, diagramas, GLOSARIO_DEFENSA.md
├── scripts/                  # scripts de simulación/test para los 5 casos
├── docker-compose.yml
├── README.md
└── .gitignore
```

`docker-compose.yml` y `infra/prometheus/prometheus.yml` ya existen con: mysql, prometheus,
grafana, node-exporter, cadvisor, demo-web (nginx). Verifica que levantan con `docker compose up -d`
antes de seguir; si no, arréglalo primero.

---

## FASE 1 (días 1-5): Agente de monitorización activa

Crea `agente/` con un servicio Python que compruebe periódicamente (configurable, por defecto cada 30s):

1. **HTTP/HTTPS**: código de respuesta, tiempo de respuesta, validación opcional de contenido esperado.
2. **Puertos TCP**: conexión simple (socket) a host:puerto.
3. **DNS**: resolución de un dominio, tiempo de resolución.
4. **Certificados SSL**: días restantes hasta caducidad de un dominio dado.
5. **Latencia (ping)**: usa `ping3` o subprocess a `ping` del sistema.

Requisitos:
- Configuración de los servicios a monitorizar en un archivo `agente/config.yml` (lista de checks con
  tipo, target, umbrales — ej. umbral de latencia "degradado" a partir de X ms).
- Cada check debe distinguir 3 estados: `OK`, `DEGRADADO`, `CAÍDO` — no un simple booleano.
- Los resultados se escriben en MySQL (tabla `checks_resultado`) y se exponen también como
  métricas Prometheus (usa `prometheus_client` de Python, expón un `/metrics` endpoint).
- Añade el agente como servicio nuevo en `docker-compose.yml` y como target de scraping en
  `infra/prometheus/prometheus.yml`.

Al terminar la fase: demuestra que si detienes `demo-web` manualmente, el agente lo detecta y lo
refleja en Prometheus/BD. Documenta esto con una captura en `docs/`.

---

## FASE 2 (días 6-10): Métricas + Motor de reglas

**Métricas (Módulo 2):**
- Confirma que Node Exporter y cAdvisor están scrapeados correctamente.
- Crea un dashboard de Grafana (`infra/grafana/dashboards/`) provisionado automáticamente vía
  Docker Compose (no manual desde la UI) con: estado de checks del agente, CPU/memoria del sistema,
  estado de contenedores.

**Motor de reglas (Módulo 3) — el módulo con más peso de diseño:**

Crea `motor-reglas/` con un motor que lea periódicamente los resultados de checks + métricas y
aplique estas reglas fijas (defínelas en `motor-reglas/reglas.yml`, no hardcodeadas en Python):

1. Servicio caído 3 comprobaciones consecutivas → alerta **crítica**.
2. Certificado SSL caduca en menos de 7 días → alerta **advertencia**.
3. Latencia media > umbral durante 10 minutos → alerta **degradado**.
4. Contenedor reiniciado > 3 veces en 5 minutos → alerta **crítica**.
5. Latencia alta + pérdida de paquetes simultánea → clasificar como "posible problema de red".
6. Error HTTP 5xx + CPU alta simultánea → clasificar como "posible saturación del servidor".

Cuando varias condiciones coincidan en ventana de tiempo (ej. reglas 5 y 6), el motor debe generar
**una única alerta consolidada** con causa probable, no una alerta por condición — este es el punto
central a defender ante el tribunal, no lo simplifiques a alertas sueltas.

Guarda cada alerta en MySQL (tabla `incidencias`: id, servicio, severidad, causa_probable,
timestamp, estado [abierta/resuelta]).

**Análisis de logs (también parte del Módulo 3, objetivo explícito del profesor — no lo dejes solo
como script de prueba puntual de la Fase 4):**

- Crea `motor-reglas/lector_logs.py`: lee periódicamente (usando Docker SDK, `container.logs()`)
  los logs de los contenedores configurados en `motor-reglas/reglas.yml` (lista de nombres de
  contenedor a vigilar).
- Cuenta apariciones de patrones configurables (por defecto: `ERROR`, `timeout`,
  `connection refused`, `database unavailable`) en una ventana de tiempo deslizante (ej. últimos
  5 minutos).
- Nueva regla 7: si la frecuencia de un patrón supera un umbral configurable en esa ventana →
  alerta (severidad según patrón: `connection refused`/`database unavailable` → crítica; `ERROR`
  genérico/`timeout` → advertencia).
- Esta señal se combina con las demás en la misma ventana de tiempo igual que las reglas 5 y 6
  (ej. errores en logs + CPU alta → misma alerta consolidada, no una alerta aparte).
- El caso 5 de la Fase 4 (`caso5_errores_logs.py`) pasa a ser la prueba de validación de esta
  capacidad ya existente, no el único sitio donde existe.

---

## FASE 3 (días 11-15): Notificaciones + Respuesta automática + API/panel

**Notificaciones (`notificaciones/`):**
- Bot de Telegram que envíe un mensaje formateado por cada incidencia nueva (severidad, servicio,
  causa probable, timestamp).
- Documenta en el README cómo crear el bot con @BotFather y qué variables de entorno hacen falta
  (`.env`, nunca subas el token al repo — verifica que `.env` está en `.gitignore`).

**Respuesta automática (`respuesta-automatica/`):**
- Si la incidencia es de tipo "contenedor caído/reiniciándose", intenta un reinicio vía Docker SDK.
- Tras el reinicio, verifica en 30s si el servicio volvió a `OK`. Si sí, notifica recuperación.
  Si no, escala la alerta (mensaje adicional marcado como "requiere intervención manual").

**API/panel de incidencias (FastAPI):**
- Endpoint simple `GET /incidencias` (con filtro por severidad/estado) y `GET /incidencias/{id}`.
  No hace falta frontend propio — esto es para consulta y para poder enseñarlo con `curl` o Swagger
  UI (FastAPI la genera sola en `/docs`) durante la defensa.
- Endpoint `GET /incidencias/{id}/informe`: genera un **informe básico post-incidente** en texto
  plano/markdown (no PDF, no hace falta más para el alcance de este TFG) con: servicio afectado,
  severidad, causa probable, timestamp de apertura y de resolución (si la tiene), duración del
  incidente, y los checks/métricas relevantes que dispararon la alerta en esa ventana de tiempo.
  Es el objetivo "generación de informe básico" que pide el profesor en el alcance recomendado.

---

## FASE 4 (días 16-18): Los 5 casos de validación

Crea en `scripts/` un script por caso que automatice la simulación y capture evidencia:

1. `caso1_caida_web.sh` — para el contenedor demo-web, verifica detección + reinicio automático.
2. `caso2_latencia.py` — introduce delay artificial en una respuesta HTTP (usa un servicio Flask
   dummy en `infra/servicios-demo/` que responda con `time.sleep()` configurable).
3. `caso3_certificado_ssl.md` — instrucciones (no todo es automatizable) para probar con un dominio
   de certificado próximo a caducar o simulado.
4. `caso4_saturacion_recursos.sh` — usa `stress-ng` en un contenedor para saturar CPU/memoria.
5. `caso5_errores_logs.py` — genera un servicio dummy que escriba errores tipo "ERROR", "timeout",
   "connection refused" en logs a una frecuencia configurable.

Para cada caso, guarda en `docs/` una captura de: (a) el dashboard de Grafana durante el incidente,
(b) el mensaje de Telegram recibido, (c) la fila de la tabla `incidencias` en MySQL.

---

## Reglas generales de trabajo

- Si en algún punto el plan de una fase no cabe en el tiempo, dilo explícitamente y propone qué
  recortar — no reduzcas silenciosamente el alcance sin decirlo.
- Actualiza `README.md` progresivamente con instrucciones de arranque (`docker compose up -d`,
  cómo correr el agente, cómo probar cada caso).
- Al final de cada fase, actualiza `docs/GLOSARIO_DEFENSA.md` con las decisiones tomadas en esa fase.
- No introduzcas ML ni llamadas a LLM en ningún módulo — está fuera de alcance para esta entrega.
