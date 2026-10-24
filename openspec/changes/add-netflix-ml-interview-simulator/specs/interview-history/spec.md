# Spec Delta

## Purpose

Guarda cada sesión de entrevista simulada solo en la máquina local, fuera del control de versiones, y resume la evolución del candidato entre sesiones de forma comparable.

## ADDED Requirements

### Requirement: Registro local de cada sesión
El sistema SHALL guardar cada sesión en un directorio propio dentro del directorio local de sesiones, identificado por fecha y un id corto. Contendrá:
- la configuración y el estado de cada instancia;
- una transcripción y un scorecard por instancia;
- los materiales (código, take-homes);
- las decisiones de corte y de debrief, si existen.

#### Scenario: Sesión completada
- **WHEN** termina una sesión de dos instancias con debrief
- **THEN** su directorio contiene la configuración, dos transcripciones, dos scorecards y la decisión

### Requirement: Sesiones fuera del repositorio
El directorio de sesiones SHALL estar en `.gitignore`. El sistema no SHALL añadir al índice, commitear ni subir archivos de sesiones, ni ofrecer hacerlo. Antes de escribir, SHALL comprobar que el directorio está ignorado y que ninguno de sus archivos está rastreado; si no se cumple, no escribirá.

#### Scenario: Directorio ignorado
- **WHEN** se crea una sesión
- **THEN** `git status` no muestra ningún archivo de la sesión

#### Scenario: Ignore ausente
- **WHEN** el directorio de sesiones no está ignorado o contiene archivos rastreados
- **THEN** el sistema no escribe la sesión, avisa e indica cómo corregirlo

#### Scenario: Fuera de un repositorio git
- **WHEN** el simulador se ejecuta fuera de un repositorio git
- **THEN** el sistema escribe la sesión y avisa de que no hay control de versiones que proteger

### Requirement: Aviso en entornos efímeros
Si detecta que corre en un entorno remoto efímero, el sistema SHALL avisar al iniciar que el historial local se pierde al reciclarse el entorno.

#### Scenario: Claude Code en la web
- **WHEN** la sesión empieza en un contenedor remoto de Claude Code
- **THEN** el resumen de configuración incluye ese aviso

### Requirement: Guardado incremental
El sistema SHALL persistir cada turno en la transcripción y actualizar el estado de la instancia, incluido el tiempo activo, tras cada turno. Así una interrupción no pierde la etapa en curso y se puede reconstruir al entrevistador.

#### Scenario: Conversación interrumpida
- **WHEN** la conversación se corta en mitad de una etapa
- **THEN** la transcripción tiene todos los turnos hasta el último, y la instancia queda "in progress" con su tiempo consumido

### Requirement: Resumen de progreso comparable
El sistema SHALL mantener, en el directorio local, un resumen de progreso que agrupe las puntuaciones por etapa, variante e id de competencia en orden cronológico, mostrando en cada punto el nivel y la versión de la rúbrica. "No evidence" no se representará como una puntuación baja, y las etapas de práctica se marcarán como tales.

#### Scenario: Repetir una etapa
- **WHEN** el candidato completa `ml-system-design@design` por segunda vez
- **THEN** el resumen muestra las dos puntuaciones de cada competencia en orden cronológico

#### Scenario: Distinto nivel o versión
- **WHEN** la repetición es a otro nivel o con otra versión de la rúbrica
- **THEN** el resumen lo indica en esos puntos y marca la ruptura de comparabilidad

#### Scenario: Consultar progreso
- **WHEN** el candidato invoca `/netflix-ml-interview progress`
- **THEN** el sistema muestra el resumen sin iniciar ninguna sesión

### Requirement: Historial de preguntas usadas
El estado de cada sesión SHALL registrar las preguntas y problemas usados en cada instancia, para que la selección de sesiones futuras pueda excluirlos.

#### Scenario: Registro de preguntas
- **WHEN** termina una instancia
- **THEN** su estado lista los ids de las preguntas o del problema usados
