# Functional Design Plan — UOW-03 Push & Scheduling

**Fecha:** 2026-03-23
**Status:** Listo para review

## Unit Context
- **Unit**: UOW-03 Push & Scheduling
- **Goal**: Programar y despachar nudges accionables por Telegram con control de frecuencia, ventana y reintentos.
- **Stories**: US-05 (Nudge accionable en Telegram), US-06 (Control de intensidad y ventana de empuje)
- **Backlog relacionado**: S3.1, S3.2, S3.3, S3.4
- **Dependencies**: UOW-02 Decision Core
- **Componentes involucrados**: scheduler/orchestrator de nudges, worker de dispatch, adaptador Telegram outbound, `ExecutionCycle`, `TaskState`

## Checklist de ejecucion

- [x] Paso 1 — Definir el modelo funcional del nudge y su ciclo de vida dentro del loop
- [x] Paso 2 — Definir la politica de scheduling diario y la creacion/cierre de `ExecutionCycle`
- [x] Paso 3 — Disenar las reglas de elegibilidad para enviar un nudge
- [x] Paso 4 — Disenar las reglas de frecuencia, intensidad y ventanas de silencio
- [x] Paso 5 — Disenar las reglas de retry y manejo de fallos transitorios de mensajeria
- [x] Paso 6 — Disenar el contenido funcional del nudge y sus guardrails de tono
- [x] Paso 7 — Disenar la telemetria minima de despacho y actividad del usuario
- [x] Paso 8 — Generar artefactos de functional design (`business-logic-model.md`, `business-rules.md`, `domain-entities.md`)

---

## Preguntas para Functional Design

### Grupo 1 — Scheduler y ciclo diario

**Q1.** Si no hay configuracion previa del usuario, ¿en que horarios default se deben programar los nudges diarios?
```md
A) 09:00, 13:00 y 18:00 hora local del usuario
B) Solo 1 nudge por la manana (09:00) para MVP
C) 09:00, 12:00 y 17:00 hora local del usuario
X) Other (please describe after [Answer]: tag below)

[Answer]: B
```

**Q2.** ¿Cuando debe crear UOW-03 el `ExecutionCycle` del dia?
```md
A) Automaticamente al inicio de la primera ventana de nudge del dia
B) A medianoche local del usuario, aunque no haya actividad
C) Solo cuando el scheduler detecta tareas priorizadas listas para empujar
X) Other (please describe after [Answer]: tag below)

[Answer]: C
```

**Q3.** ¿Cuando se considera cerrado el `ExecutionCycle` para esta unidad?
```md
A) Al final del dia (23:59 local) aunque no haya respuestas
B) Despues del ultimo nudge programado del dia
C) UOW-03 no cierra el ciclo; solo lo abre y UOW-05 lo cierra
X) Other (please describe after [Answer]: tag below)

[Answer]: C
```

### Grupo 2 — Elegibilidad y contenido del nudge

**Q4.** ¿Que tarea debe usar el sistema para construir el nudge?
```md
A) Siempre la tarea #1 del Top 3 actual
B) La tarea #1, pero si ya fue nudged hoy pasar a la siguiente elegible
C) El sistema puede elegir cualquiera de las 3 segun heuristica simple
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

**Q5.** Si no existe Top 3 cacheado o vigente al momento de la ventana, ¿que hace el scheduler?
```md
A) Recalcula Top 3 en ese momento y usa el resultado
B) No envia nudge y espera a la siguiente ventana
C) Envia un recordatorio generico sin tarea concreta
X) Other (please describe after [Answer]: tag below)

[Answer]: B
```

**Q6.** ¿Que formato funcional debe tener el nudge del MVP?
```md
A) Un solo mensaje con la tarea prioritaria + botones inline `✓ Hecho`, `⏸ Posponer`, `? Aclarar`
B) Igual que A pero incluyendo tambien una linea corta con razon de prioridad
C) Mensaje minimalista con solo la tarea y sin explicacion adicional
X) Other (please describe after [Answer]: tag below)

[Answer]: B
```

### Grupo 3 — Frecuencia, intensidad y ventanas

**Q7.** El backlog dice maximo 3 nudges por dia. ¿Ese limite debe ser fijo para todos en MVP?
```md
A) Si, fijo para todos: maximo 3 por dia
B) Si, pero con opcion de bajar a 1 o 2 por usuario
C) No, debe ser totalmente configurable por usuario desde el inicio
X) Other (please describe after [Answer]: tag below)

[Answer]: X en principio y estandar 3 por dia pero el usuario con algun comando /config podria cambiarlo
```

**Q8.** Si el usuario tuvo actividad reciente, ¿cuanto tiempo de silencio operacional bloquea el nudge programado?
```md
A) 30 minutos
B) 60 minutos
C) 90 minutos
X) Other (please describe after [Answer]: tag below)

[Answer]: B
```

**Q9.** La ventana de silencio de S3.3, para esta unidad, ¿como quieres modelarla en MVP?
```md
A) Un solo rango por dia que aplica a todos los dias de la semana
B) Multiples rangos por dia desde el inicio
C) Solo una preferencia simple de "no molestar en la manana/tarde/noche"
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

### Grupo 4 — Retry, fallos y reenganche

**Q10.** Si falla el envio de Telegram por error transitorio, ¿cual debe ser la politica de retry del MVP?
```md
A) 3 intentos con backoff corto dentro de la misma ventana
B) 1 reintento unico y luego abortar
C) Sin retry automatico en MVP; solo loggear el fallo
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

**Q11.** Si todos los intentos fallan, ¿que registro minimo quieres dejar?
```md
A) Evento de fallo en `ExecutionCycle` con motivo y timestamp
B) Solo log estructurado; sin persistencia adicional
C) Evento + contador de fallos por ciclo/usuario
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

**Q12.** S3.4 habla de reenganche por inactividad >24h. ¿Quieres incluir ese flujo dentro de UOW-03 o dejarlo para una segunda pasada de la unidad?
```md
A) Si, incluirlo ahora como parte de UOW-03
B) No, dejar solo scheduler base + nudge normal; reenganche despues
C) Disenarlo ahora pero implementarlo despues
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

### Grupo 5 — Guardrails de tono y trazabilidad

**Q13.** Para el tono del nudge, ¿que estilo prefieres como baseline?
```md
A) Directo y breve, con acompanamiento neutral
B) Motivacional suave, pero sin elogio exagerado
C) Minimalista casi operativo, sin framing emocional
X) Other (please describe after [Answer]: tag below)

[Answer]: B
```

**Q14.** ¿Que telemetria minima debe registrar UOW-03 en el ciclo?
```md
A) `NUDGE_SCHEDULED`, `NUDGE_SENT`, `NUDGE_SKIPPED_ACTIVITY`, `NUDGE_FAILED`
B) Solo `NUDGE_SENT` y `NUDGE_FAILED`
C) A + metadatos de ventana usada y task_id objetivo
X) Other (please describe after [Answer]: tag below)

[Answer]: C
```
