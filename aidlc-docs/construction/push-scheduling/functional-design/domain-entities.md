# Domain Entities — UOW-03 Push & Scheduling

## Nuevas entidades / conceptos funcionales

UOW-03 no necesita introducir un gran numero de tablas nuevas para el MVP. Su foco
principal es extender entidades ya existentes (`TaskState`, `ExecutionCycle`) y
definir el contrato funcional del despacho de nudges.

---

## Entity: NudgeDispatch

Representa un intento de empuje proactivo sobre una tarea priorizada dentro de una
ventana concreta. Puede persistirse como evento o como metadata embebida en el ciclo,
segun la implementacion final, pero funcionalmente existe como entidad del dominio.

| Field | Type | Required | Description |
|---|---|---|---|
| dispatchId | string (UUID) | Yes | Identificador del intento de dispatch |
| cycleId | string | Yes | `ExecutionCycle` al que pertenece |
| userId | string | Yes | Owner del dispatch |
| taskId | string | Yes | Tarea objetivo del nudge |
| windowStart | DateTime | Yes | Inicio de ventana evaluada |
| windowEnd | DateTime | Yes | Fin de ventana evaluada |
| status | NudgeDispatchStatus | Yes | Resultado del dispatch |
| attemptCount | int | Yes | Numero de intentos realizados |
| reason | string or null | No | Motivo de skip o fallo |
| createdAt | DateTime | Yes | Momento de evaluacion inicial |
| sentAt | DateTime or null | No | Momento de envio exitoso |

### NudgeDispatchStatus

| Status | Description |
|---|---|
| `scheduled` | La ventana fue evaluada y el dispatch fue preparado |
| `sent` | El mensaje fue enviado correctamente |
| `skipped_activity` | No se envio porque hubo actividad reciente |
| `skipped_no_top3` | No se envio porque no habia Top 3 vigente |
| `failed` | Todos los intentos fallaron |

**Nota:** aunque la implementacion final pueda modelarlo como eventos en vez de tabla
dedicada, estos estados deben existir funcionalmente.

---

## Entity Extension: ExecutionCycle

`ExecutionCycle` ya existe desde UOW-02. En UOW-03 se amplía su responsabilidad para
servir como contenedor del dispatch diario.

### Campos existentes usados por esta unidad

| Field | Uso en UOW-03 |
|---|---|
| `cycleId` | Correlacion de eventos de dispatch |
| `userId` | Owner del ciclo |
| `date` | Ciclo diario |
| `status` | El ciclo debe estar `active` para recibir eventos |
| `top3TaskIds` | Referencia del ranking vigente |

### Nuevos conceptos funcionales asociados

| Concepto | Description |
|---|---|
| `nudgeCount` | Cantidad de nudges automaticos enviados hoy |
| `lastActivityAt` | Ultimo timestamp de actividad relevante del loop |
| `lastNudgedTaskId` | Ultima tarea empujada en el ciclo |

**Constraint funcional:** UOW-03 puede crear el ciclo si existe oportunidad real de
dispatch, pero no lo cierra.

---

## Entity Extension: TaskState

`TaskState` es la entidad objetivo del push.

### Campos relevantes

| Field | Uso en UOW-03 |
|---|---|
| `taskId` | Identificador de la tarea objetivo |
| `userId` | Owner |
| `normalizedText` | Texto visible en el nudge |
| `status` | Elegibilidad y transicion de estado |
| `deadline` | Puede alimentar la razon corta de prioridad |
| `snoozeCount` | Util para contexto posterior de reenganche |

### Estado relevante

| Status | Description | Usado por |
|---|---|---|
| `prioritized` | Tarea lista para ser elegida por el scheduler | UOW-02 / UOW-03 |
| `nudged` | Nudge enviado, esperando respuesta | UOW-03 |
| `done` | Tarea completada | UOW-04 |
| `snoozed` | Tarea pospuesta | UOW-04 |
| `needs_clarification` | Tarea en aclaracion | UOW-02 / UOW-04 |

### Nueva transicion funcional

```text
prioritized -> nudged
```

Trigger:

- envio exitoso del nudge

---

## Entity: UserNudgePreferences

Representa la configuracion minima de intensidad y silencio del usuario para el MVP.
Puede terminar persistida dentro de `energy_profiles` o en otra estructura, pero
funcionalmente esta entidad existe.

| Field | Type | Required | Description |
|---|---|---|---|
| userId | string | Yes | Owner |
| timezone | string | Yes | Timezone operativa del usuario |
| maxNudgesPerDay | int | Yes | Limite diario, default 3 |
| silenceStart | time or null | No | Inicio de ventana de silencio |
| silenceEnd | time or null | No | Fin de ventana de silencio |
| updatedAt | DateTime | Yes | Ultima actualizacion |

### Constraint

- En MVP existe un solo rango diario de silencio por usuario.
- `maxNudgesPerDay` default es 3, aunque puede abrirse override futuro via `/config`.

---

## Value Object: NudgeMessage

Representa el contenido final que se enviara a Telegram.

| Field | Type | Description |
|---|---|---|
| `taskTitle` | string | Titulo o texto visible de la tarea |
| `priorityReason` | string | Razon corta de por que va primero |
| `toneProfile` | string | Perfil de tono aplicado (`soft_motivational`) |
| `buttons` | list[string] | `done`, `snooze`, `clarify` |

**Constraint:** el contenido debe respetar guardrails de tono no acusatorio.

---

## Eventos funcionales de la unidad

| Event | Description | Metadata minima |
|---|---|---|
| `NUDGE_SCHEDULED` | Se evaluo y preparo un intento de push | `task_id`, ventana, timestamp |
| `NUDGE_SENT` | El mensaje fue enviado correctamente | `task_id`, ventana, timestamp |
| `NUDGE_SKIPPED_ACTIVITY` | Se omitio por actividad reciente | ventana, timestamp, motivo |
| `NUDGE_FAILED` | Fallaron todos los intentos | `task_id`, ventana, timestamp, motivo |

---

## Relacion entre entidades

```text
ExecutionCycle 1 --- N NudgeDispatch
ExecutionCycle 1 --- N TaskState (via top3TaskIds / eventos)
UserNudgePreferences 1 --- 1 User
NudgeDispatch N --- 1 TaskState
```

UOW-03 mantiene la responsabilidad principal sobre:

- decidir si hay o no dispatch;
- elegir la tarea objetivo;
- registrar el resultado del empuje;
- mover la tarea a `nudged` cuando el envio fue exitoso.
