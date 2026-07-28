# Glosario para la defensa del TFG

Cada entrada explica un concepto o una decisión de diseño en lenguaje sencillo, pensado para
estudiar antes de la defensa oral.

## Conceptos base

**Contenedor** → Es como una caja aislada que lleva dentro un programa con todo lo que necesita
para funcionar (sus librerías, su configuración), sin depender de lo que haya instalado en el
ordenador anfitrión. Así el mismo programa funciona igual en tu portátil que en un servidor.

**Docker Compose** → Un archivo (`docker-compose.yml`) que describe qué contenedores quieres
levantar y cómo se conectan entre sí (por ejemplo, "Grafana necesita hablar con Prometheus").
Con un solo comando (`docker compose up -d`) se arrancan todos a la vez, ya conectados.

**Variable de entorno** → Un valor de configuración (como una contraseña) que se le pasa a un
programa desde fuera del código, en vez de escribirlo directamente en los ficheros. Así se pueden
cambiar credenciales sin tocar el código, y evitar subir secretos al repositorio.

**Endpoint** → Una "puerta de entrada" concreta de un servicio, identificada por una URL, a la que
se le puede pedir información o una acción (ej. `GET /incidencias` pide la lista de incidencias).

## Decisiones de diseño — infraestructura base

**Elijo MySQL para las incidencias** → porque es una base de datos relacional robusta y de uso muy
extendido en la industria, adecuada para guardar registros estructurados (checks, incidencias) con
relaciones claras entre tablas. Se elige frente a otras opciones por ser la que el autor ya conoce
de antes, lo que permite centrar el tiempo del TFG en el diseño del sistema y no en aprender una
base de datos nueva.

**Elijo Prometheus + Grafana en vez de un panel propio** → Prometheus recoge y guarda métricas
numéricas a lo largo del tiempo (por ejemplo, "CPU al 80% a las 10:03"), y Grafana las dibuja en
gráficas. Usar herramientas ya existentes y estándar de la industria evita reinventar un sistema
de visualización desde cero, que no es el foco de este TFG.

**Elijo Node Exporter y cAdvisor** → Node Exporter expone métricas del sistema operativo
(CPU, memoria, disco de la máquina). cAdvisor expone métricas de cada contenedor Docker por
separado (cuánta CPU/memoria usa cada uno). Juntos dan visibilidad completa: máquina + contenedores.

**demo-web (nginx) como servicio de prueba** → un servidor web mínimo que se usa como "víctima" en
los casos de validación: se puede parar, ralentizar o saturar de forma controlada para comprobar
que el sistema de monitorización lo detecta correctamente.

## Fase 1 — Agente de monitorización activa

**Monitorización activa** → en vez de esperar a que un servicio avise de que falla, el agente
"pregunta" él mismo cada cierto tiempo (cada 30s) si cada servicio responde bien. Es la diferencia
entre esperar una llamada de auxilio y llamar tú para comprobar que todo va bien.

**Los 5 tipos de check del agente** → HTTP (¿responde la web y con qué código y tiempo?), TCP
(¿se puede abrir una conexión a un puerto?), DNS (¿se resuelve un dominio a una IP y en cuánto
tiempo?), certificado SSL (¿cuántos días quedan hasta que caduque el certificado de seguridad de
un dominio?), y ping (¿cuánto tarda un paquete en ir y volver a un host?).

**Tres estados en vez de un booleano (OK/DEGRADADO/CAÍDO)** → un simple "funciona o no funciona"
no distingue entre un servicio totalmente caído y uno que responde pero muy lento. Con tres
estados el sistema puede avisar de una degradación progresiva antes de que se convierta en una
caída total, que es justo el objetivo central del TFG (no solo detectar caídas, sino
degradaciones).

**`agente/config.yml`** → los servicios a vigilar y sus umbrales (ej. "por encima de 300ms se
considera degradado") están en un archivo de configuración separado del código Python. Así se
puede añadir o ajustar un check sin tocar el programa, y queda documentado en un solo sitio.

**`prometheus_client` y el endpoint `/metrics`** → el agente expone sus resultados en una URL
(`/metrics`) con un formato de texto estándar que Prometheus entiende y "scrapea" (lee) cada
15 segundos automáticamente. Es el mismo mecanismo que usan Node Exporter y cAdvisor, así que
Prometheus trata al agente como una fuente de métricas más.

**PyMySQL + `cryptography`** → la librería usada para conectar el agente (Python) a MySQL. MySQL 8
usa por defecto un método de login (`caching_sha2_password`) que necesita cifrado RSA, y para eso
PyMySQL necesita el paquete `cryptography` instalado; si falta, la conexión falla con un error de
autenticación aunque el usuario y la contraseña sean correctos.

**ping3 (ping en Python puro)** → en vez de llamar al comando `ping` del sistema operativo, se usa
una librería que crea directamente el paquete de red en Python. Evita depender de que el binario
`ping` esté instalado dentro del contenedor y simplifica el `Dockerfile`.

## Fase 2 — Dashboard de Grafana y motor de reglas

**Dashboard provisionado (no manual)** → en vez de crear el dashboard a mano desde la interfaz
web de Grafana (que se perdería si se borra el contenedor), el dashboard está definido en un
archivo JSON (`infra/grafana/dashboards/monitorizacion.json`) que Grafana carga automáticamente
al arrancar. Así el dashboard forma parte del repositorio, versionado igual que el código.

**Motor de reglas (`motor-reglas/`)** → un segundo programa Python, separado del agente, que cada
30s lee los resultados que el agente ya guardó en MySQL, consulta métricas en Prometheus (CPU) y
consulta al propio Docker (reinicios de contenedores, logs), y decide si esas señales combinadas
representan una incidencia real. El agente solo "mide"; el motor de reglas "interpreta".

**`motor-reglas/reglas.yml`** → igual que con el agente, los umbrales y qué se vigila (qué
contenedores, qué patrones de log, qué checks) están en un archivo de configuración, no en el
código Python. Esto permite añadir un nuevo servicio a vigilar sin tocar la lógica del motor.

**Consolidación de alertas (el punto central de la Fase 2)** → cuando dos señales relacionadas
ocurren a la vez (ej. latencia alta + pérdida de paquetes), el motor no genera dos alertas
sueltas: las combina en una sola incidencia con una causa probable conjunta ("posible problema
de red"). Esto evita que el equipo de guardia reciba una avalancha de notificaciones separadas
para lo que en realidad es un solo problema. La lista de qué señales se combinan y con qué
nombre está en `reglas.yml` (sección `correlaciones`), no hardcodeada en Python.

**Ciclo de vida de una incidencia (abierta → resuelta)** → una incidencia se crea la primera vez
que se cumple una condición, y se marca automáticamente como resuelta en cuanto esa condición
deja de cumplirse, sin que nadie tenga que cerrarla a mano. Mientras la condición se mantenga, no
se crean incidencias duplicadas cada 30s: se reutiliza la misma fila abierta.

**`valor_extra` en `checks_resultado`** → columna numérica genérica añadida en la Fase 2 para que
el motor de reglas pueda comparar valores exactos (código HTTP, días restantes de un certificado)
sin tener que interpretar el texto libre de `detalle`. Su significado depende del tipo de check
(código de estado para HTTP, días para SSL, vacío para el resto) — es más simple que añadir una
columna nueva por cada tipo de check.

**Docker SDK montando `/var/run/docker.sock` en modo solo lectura** → el motor de reglas necesita
preguntarle a Docker cuántas veces se ha reiniciado un contenedor y leer sus logs, así que se le
da acceso al socket de Docker del host. Se monta como `:ro` (solo lectura) porque en esta fase
el motor solo *consulta* información, no la modifica; la capacidad de reiniciar contenedores
(que sí necesita permiso de escritura) se añade en la Fase 3 con `respuesta-automatica/`.

**Severidades: solo 3 niveles (informativa, advertencia, crítica)** → siguiendo el encargo
original del profesor, todas las reglas usan una de estas 3 severidades. La regla de "latencia
media alta" se clasifica como `advertencia` (no se inventa un cuarto nivel "degradado") para
mantener una escala de severidad consistente en toda la base de datos de incidencias.

**`PYTHONUNBUFFERED=1`** → variable de entorno que le dice a Python que no "amontone" la salida
de los `print()` en un buffer antes de mostrarla. Sin esto, los logs de un contenedor Docker
pueden tardar mucho en aparecer (o no aparecer hasta que el proceso termina), lo cual dificulta
depurar problemas en producción.

**`charset="utf8mb4"` en la conexión a MySQL** → sin especificarlo, la librería PyMySQL usa por
defecto una codificación antigua (`latin1`) para hablar con MySQL, lo que corrompe cualquier
acento o carácter especial guardado (ej. "días" se guardaba mal). Especificar `utf8mb4`
explícitamente asegura que el español con tildes se guarda y se lee correctamente.
