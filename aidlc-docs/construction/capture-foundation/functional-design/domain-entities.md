# Domain Entities — UOW-01 Capture Foundation

## Entity: Intent

Representa la intencion cruda capturada desde el canal de entrada (Telegram).

| Field | Type | Required | Description |
|---|---|---|---|
| intentId | string (UUID) | Yes | Identificador unico de la intencion |
| userId | string | Yes | Identificador del usuario en Telegram |
| rawText | string | Yes | Texto original tal como lo envio el usuario |
| source | string | Yes | Canal de origen (siempre `telegram` en MVP) |
| createdAt | DateTime (ISO 8601) | Yes | Timestamp de recepcion |

**Notes**:
- Intent es una entidad transitoria: se transforma en una o mas TaskState tras normalizacion.
- El rawText se preserva intacto para trazabilidad.

---

## Entity: TaskState

Representa una tarea normalizada y operable dentro del loop.

| Field | Type | Required | Description |
|---|---|---|---|
| taskId | string (UUID) | Yes | Identificador unico de la tarea |
| userId | string | Yes | Owner de la tarea |
| originalText | string | Yes | Texto original del usuario (preservado) |
| normalizedText | string | Yes | Texto procesado (trimmed, cleaned) |
| tag | string or null | No | Etiqueta opcional extraida de hashtag (ej: `trabajo`) |
| deadline | DateTime or null | No | Deadline/urgencia opcional extraida del texto |
| status | TaskStatus | Yes | Estado actual en el ciclo de vida |
| sourceIntentId | string (UUID) | Yes | Referencia al Intent que origino esta tarea |
| createdAt | DateTime (ISO 8601) | Yes | Timestamp de creacion |
| updatedAt | DateTime (ISO 8601) | Yes | Timestamp de ultima actualizacion |

### TaskStatus Enum (Lifecycle)

```
captured -> pending -> prioritized -> nudged -> done
                                           -> snoozed -> pending
                                           -> clarifying -> pending
```

| Status | Description | Set By |
|---|---|---|
| `captured` | Recien capturada, aun no disponible para priorizacion | UOW-01 (Capture) |
| `pending` | Lista para priorizacion por el Decision Engine | UOW-01 (post-normalizacion) o UOW-04 (post-snooze/clarify) |
| `prioritized` | Incluida en Top 3 actual | UOW-02 (Decision) |
| `nudged` | Nudge enviado, esperando respuesta | UOW-03 (Push) |
| `done` | Completada por el usuario | UOW-04 (Respond) |
| `snoozed` | Pospuesta temporalmente | UOW-04 (Respond) |
| `clarifying` | En proceso de aclaracion | UOW-04 (Respond) |

**Note**: Para UOW-01, solo se usan los estados `captured` y `pending`. Los demas estados se definen aqui para contexto completo del ciclo de vida pero se implementan en UOW-02..04.

---

## Entity: CaptureEvent

Evento minimo registrado al capturar una intencion.

| Field | Type | Required | Description |
|---|---|---|---|
| eventId | string (UUID) | Yes | Identificador unico del evento |
| eventType | string | Yes | Siempre `INTENT_CAPTURED` para este flujo |
| taskId | string (UUID) | Yes | Referencia a la tarea creada |
| userId | string | Yes | Usuario que capturo |
| originalText | string | Yes | Texto original capturado |
| timestamp | DateTime (ISO 8601) | Yes | Momento del evento |
| correlationId | string (UUID) | Yes | ID de correlacion para trazabilidad del flujo |

---

## Entity: DedupRecord

Registro interno para control de deduplicacion.

| Field | Type | Required | Description |
|---|---|---|---|
| userId | string | Yes | Usuario |
| exactText | string | Yes | Texto exacto del mensaje |
| lastSeenAt | DateTime | Yes | Ultima vez que se vio este texto exacto |
| taskId | string (UUID) | Yes | Tarea asociada al primer registro |

**TTL**: Los registros expiran automaticamente despues de 5 minutos (ventana de deduplicacion).
