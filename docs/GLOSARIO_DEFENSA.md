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
