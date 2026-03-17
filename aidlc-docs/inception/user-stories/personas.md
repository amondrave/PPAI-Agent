# Personas — PPAI v1

## Persona 1: Executor Freelancer (Usuario Final)

### Profile
- Profesional independiente técnico en LATAM
- Gestiona trabajo de clientes + proyectos propios
- Usa Telegram de forma continua durante el día

### Core Goals
- Arrancar rápido sin fricción cuando hay muchas tareas
- Evitar bloqueo por ambigüedad o sobrecarga
- Cerrar al menos una tarea clave diaria con consistencia

### Main Pains
- Backlog largo sin criterio claro de arranque
- Tendencia a posponer tareas difíciles
- Culpa al final del día por baja ejecución real

### Behavioral Signals Relevant to PPAI
- Latencia entre nudge y acción
- Frecuencia de `done` vs `snooze`
- Horas del día con mayor respuesta efectiva

### Success Definition
- Recibir un “siguiente paso” claro y accionable
- Completar tareas sin tener que replanificar todo
- Obtener cierre diario útil, no acusatorio

## Persona 2: Loop Operator (Operador/Admin)

### Profile
- Responsable de configurar reglas y operación del sistema
- Supervisa calidad de priorización, nudges y reportes

### Core Goals
- Mantener loop confiable y trazable
- Ajustar reglas sin romper consistencia del sistema
- Monitorear señales de bloqueo, rescate y ejecución

### Main Pains
- Dificultad para detectar por qué cae la ejecución
- Riesgo de nudge demasiado agresivo o inefectivo
- Necesidad de cambios rápidos en reglas con bajo riesgo

### Success Definition
- Reglas claras, versionables y auditables
- Métricas mínimas disponibles para iterar
- Comportamiento del sistema consistente con guardrails

## Persona-to-Requirement Coverage
- Persona 1: FR-01, FR-02, FR-03, FR-04, FR-05, FR-06
- Persona 2: FR-02, FR-03, FR-07, FR-08, NFR-01, NFR-04, NFR-05
