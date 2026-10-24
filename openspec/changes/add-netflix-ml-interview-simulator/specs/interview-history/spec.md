# Spec Delta

## Purpose

Guarda de forma persistente y legible cada sesión de entrevista simulada y resume la evolución del candidato entre sesiones, para que pueda medir su progreso.

## ADDED Requirements

### Requirement: Registro de cada sesión
El sistema SHALL guardar cada sesión en un directorio propio, identificado por fecha y un identificador corto. El directorio SHALL contener la configuración, el estado de cada etapa, una transcripción por etapa, un scorecard por etapa evaluada y, si existe, el veredicto del comité. Todo en archivos markdown o YAML legibles.

#### Scenario: Sesión completada
- **WHEN** termina una sesión de dos etapas con veredicto
- **THEN** el directorio de la sesión contiene la configuración, dos transcripciones, dos scorecards y el veredicto

### Requirement: Guardado incremental
El sistema SHALL persistir la transcripción de una etapa a medida que avanza, como mínimo tras cada turno del candidato, para que una interrupción no pierda la etapa en curso.

#### Scenario: Conversación interrumpida
- **WHEN** la conversación se corta en mitad de una etapa
- **THEN** la transcripción guardada contiene todos los turnos hasta el último respondido y la etapa queda marcada "en curso"

### Requirement: Resumen de progreso
El sistema SHALL mantener un resumen de progreso que liste las sesiones con su fecha, rol, nivel, etapas y señales, y que muestre la tendencia por competencia en las etapas repetidas.

#### Scenario: Repetir una etapa
- **WHEN** el candidato completa `ml-system-design` por segunda vez
- **THEN** el resumen muestra las dos puntuaciones por competencia de esa etapa en orden cronológico

#### Scenario: Consultar progreso
- **WHEN** el candidato invoca `/netflix-ml-interview progreso`
- **THEN** el sistema muestra el resumen sin iniciar ninguna sesión

### Requirement: Persistencia más allá del contenedor
Al terminar o pausar una sesión, el sistema SHALL ofrecer hacer commit del directorio de la sesión y del resumen de progreso, porque el entorno puede ser efímero. No SHALL hacer commit sin la confirmación del candidato.

#### Scenario: Candidato acepta
- **WHEN** el candidato confirma guardar al terminar la sesión
- **THEN** el sistema hace commit solo de los archivos de esa sesión y del resumen de progreso

#### Scenario: Candidato rechaza
- **WHEN** el candidato rechaza el commit
- **THEN** los archivos quedan en el disco y el sistema avisa de que pueden perderse si el entorno se recicla

### Requirement: Evitar repetir preguntas
Al preparar una etapa ya realizada en sesiones anteriores, el sistema SHALL evitar repetir las preguntas principales ya usadas mientras queden alternativas en el banco para el rol y nivel.

#### Scenario: Segunda vez en coding
- **WHEN** el candidato hace `coding` por segunda vez con el mismo rol y nivel
- **THEN** el problema principal es distinto del de la sesión anterior
