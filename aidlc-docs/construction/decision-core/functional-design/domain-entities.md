# Domain Entities — UOW-02 Decision Core

## Entidades nuevas en UOW-02

---

## Entity: ExecutionCycle

Representa un ciclo de trabajo diario del usuario. Un ciclo agrupa todos los eventos
de decisión, nudge y respuesta que ocurren en un día calendario.

| Field | Type | Required | Description |
|---|---|---|---|
| cycleId | string (UUID) | Yes | Identificador único del ciclo |
| userId | string | Yes | Owner del ciclo |
| date | string (YYYY-MM-DD) | Yes | Fecha del ciclo (un ciclo por usuario por día) |
| status | CycleStatus | Yes | Estado del ciclo |
| top3TaskIds | list[string] | No | IDs de las tareas en el Top 3 actual presentado |
| manualReorders | int | Yes | Número de reordenamientos manuales en este ciclo (default: 0) |
| createdAt | DateTime (ISO 8601) | Yes | Timestamp de creación |
| closedAt | DateTime or null | No | Timestamp de cierre (null si aún activo) |

### CycleStatus Enum

| Status | Description | Set By |
|---|---|---|
| `active` | Ciclo en curso | UOW-03 (scheduler) o UOW-02 (fallback si no existe) |
| `closed` | Ciclo cerrado al final del día | UOW-03 o UOW-05 |

**Constraint**: Máximo 1 ciclo con status `active` por usuario en cualquier momento.
**Creación**: El scheduler (UOW-03) crea el ciclo al inicio del día. UOW-02 crea uno
en modo fallback si no existe (permite operar sin UOW-03 en desarrollo/tests).

---

## Value Object: PriorityScore

Puntuación calculada para una tarea elegible. No se persiste en DB — se computa
en memoria durante cada evaluación de Top 3.

| Field | Type | Description |
|---|---|---|
| taskId | string | Referencia a TaskState |
| urgencyScore | int (0–10) | Puntuación de urgencia (ver reglas) |
| ageScore | int (0–7) | Puntuación de antigüedad en días |
| snoozeScore | int (0–10) | Puntuación de presión por posposiciones |
| totalScore | int (0–27) | Suma de los tres factores |
| explanation | string | Texto legible para auditoría |

**Ejemplo de explanation:** `"urgencia alta (deadline hoy) + 3 días pendiente + pospuesta 2 veces"`

---

## Value Object: Top3Result

Resultado de una evaluación de priorización. Se usa para presentar el Top 3 al usuario
y para registrar el evento en el ExecutionCycle.

| Field | Type | Description |
|---|---|---|
| cycleId | string | Ciclo al que pertenece esta evaluación |
| userId | string | Usuario evaluado |
| rankedScores | list[PriorityScore] | 1–3 items ordenados por totalScore desc |
| generatedAt | DateTime | Momento de la evaluación |

---

## Entidades heredadas de UOW-01 (sin modificación en UOW-02)

| Entidad | Campos relevantes para UOW-02 | Transición de estado |
|---|---|---|
| TaskState | taskId, userId, normalizedText, deadline, status, snoozeCount*, createdAt | `pending` → `prioritized` al incluirse en Top 3 |

> **Nota**: `snoozeCount` es un campo nuevo que UOW-02 requiere en `TaskState`.
> Se añadirá al esquema DynamoDB en el step de Infrastructure Design de esta unidad.
> En UOW-01 su valor es siempre 0 (las tareas recién capturadas no tienen snoozes).
