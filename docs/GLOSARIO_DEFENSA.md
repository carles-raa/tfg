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
