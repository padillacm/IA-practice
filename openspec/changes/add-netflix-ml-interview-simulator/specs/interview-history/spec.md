# Spec Delta

## Purpose

Guarda cada sesión de entrevista simulada solo en la máquina local, fuera del control de versiones, y resume la evolución del candidato entre sesiones para que pueda medir su progreso.

## ADDED Requirements

### Requirement: Registro local de cada sesión
El sistema SHALL guardar cada sesión en un directorio propio, identificado por fecha y un identificador corto, dentro del directorio local de sesiones. Ese directorio SHALL contener la configuración, el estado de cada etapa, una transcripción por etapa, un scorecard por etapa evaluada, los materiales de la sesión (código y take-homes) y, si existe, la decisión del debrief.

#### Scenario: Sesión completada
- **WHEN** termina una sesión de dos etapas con debrief
- **THEN** el directorio de la sesión contiene la configuración, dos transcripciones, dos scorecards y la decisión

### Requirement: Sesiones fuera del repositorio
El directorio de sesiones SHALL estar en `.gitignore`. El sistema no SHALL añadir al índice, commitear ni subir ningún archivo de sesiones, ni ofrecer hacerlo. Antes de escribir la primera sesión, SHALL comprobar que el directorio está ignorado por git y negarse a guardar si no lo está.

#### Scenario: Directorio ignorado
- **WHEN** se crea una sesión
- **THEN** `git status` no muestra ningún archivo de esa sesión

#### Scenario: Ignore ausente
- **WHEN** el directorio de sesiones no está ignorado por git (p. ej. se borró la entrada de `.gitignore`)
- **THEN** el sistema no escribe la sesión, avisa al candidato e indica la línea que debe restaurar

#### Scenario: Fin de sesión
- **WHEN** termina o se pausa una sesión
- **THEN** el sistema no propone ningún commit y solo indica dónde quedaron los archivos locales

### Requirement: Aviso en entornos efímeros
Si el sistema detecta que corre en un entorno remoto efímero, SHALL avisar al iniciar la sesión de que los archivos locales se pierden cuando se recicla el entorno.

#### Scenario: Claude Code en la web
- **WHEN** la sesión empieza en un contenedor remoto de Claude Code
- **THEN** el resumen de configuración incluye un aviso de que el historial no persistirá más allá del contenedor

### Requirement: Guardado incremental
El sistema SHALL persistir la transcripción de una etapa a medida que avanza, como mínimo tras cada turno del candidato, para que una interrupción no pierda la etapa en curso.

#### Scenario: Conversación interrumpida
- **WHEN** la conversación se corta en mitad de una etapa
- **THEN** la transcripción guardada contiene todos los turnos hasta el último respondido y la etapa queda marcada "in progress"

### Requirement: Resumen de progreso
El sistema SHALL mantener, en el mismo directorio local, un resumen de progreso que liste las sesiones con fecha, rol, nivel, etapas y recomendaciones, y que muestre la tendencia por competencia en las etapas repetidas.

#### Scenario: Repetir una etapa
- **WHEN** el candidato completa `ml-system-design` por segunda vez
- **THEN** el resumen muestra las dos puntuaciones por competencia de esa etapa en orden cronológico

#### Scenario: Consultar progreso
- **WHEN** el candidato invoca `/netflix-ml-interview progress`
- **THEN** el sistema muestra el resumen sin iniciar ninguna sesión

### Requirement: Evitar repetir preguntas
Al preparar una etapa ya hecha en sesiones locales anteriores, el sistema SHALL evitar repetir las preguntas principales ya usadas mientras queden alternativas en el banco para el rol y el nivel.

#### Scenario: Segunda vez en coding
- **WHEN** el candidato hace `coding` por segunda vez con el mismo rol y nivel
- **THEN** el problema principal es distinto del de la sesión anterior
