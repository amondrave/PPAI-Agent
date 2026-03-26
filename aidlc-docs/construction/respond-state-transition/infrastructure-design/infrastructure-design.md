# Infrastructure Design — UOW-04 Respond & State Transition

> Todo el stack base (ECS Fargate, DynamoDB, ECR, VPC, CloudWatch, OIDC) se hereda
> de UOW-01/02/03. UOW-04 **no crea recursos nuevos**. Este documento describe
> únicamente el delta de configuración sobre recursos existentes.

---

## Delta de infraestructura

### 1. DynamoDB — Habilitar TTL en `ppai-events`

| Atributo | Valor |
|---|---|
| Tabla | `${var.table_prefix}-events` (existente) |
| TTL attribute | `ttl` (Number — epoch seconds) |
| Retención | 90 días desde timestamp del evento |

**Cambio en Terraform:**

```hcl
resource "aws_dynamodb_table" "events" {
  # ... configuración existente ...

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}
```

**Impacto en datos existentes:**
- Los `CaptureEvent` de UOW-01 no tienen atributo `ttl` → no se eliminan (comportamiento correcto de DynamoDB TTL).
- Solo los nuevos `InteractionEvent` de UOW-04 incluyen `ttl = timestamp_epoch + 7_776_000` (90 días en segundos).

---

### 2. DynamoDB — Nuevos atributos en `ppai-tasks` (sin migración)

DynamoDB es schemaless. Los nuevos campos se agregan en código sin modificar la tabla:

| Campo | Tipo DynamoDB | Presente cuando | Descripción |
|---|---|---|---|
| `snoozedUntil` | S (ISO 8601) | `status = snoozed` | UTC timestamp cuando expira el cooldown de snooze |
| `completedAt` | S (ISO 8601) | `status = done` | UTC timestamp cuando se completó la tarea |

**Sin GSI nuevo.** El filtro de `snoozedUntil` se aplica en aplicación al momento de `list_pending`:
```python
pending = [t for t in tasks if t.snoozed_until is None or t.snoozed_until <= now]
```

---

### 3. DynamoDB — Nuevos event types en `ppai-cycles`

La tabla `ppai-cycles` ya soporta un array `nudgeEvents` por ciclo. UOW-04 agrega nuevos `eventType` al mismo array:

| Event Type | Trigger | Metadata |
|---|---|---|
| `INTERACTION_DONE` | Usuario confirma Done | `task_id`, `completed_at` |
| `INTERACTION_SNOOZED` | Usuario presiona Snooze | `task_id`, `snooze_count`, `snoozed_until` |
| `INTERACTION_CLARIFIED` | Usuario presiona Clarify | `task_id` |
| `INTERACTION_CLARIFY_RESOLVED` | Usuario envía texto de aclaración | `task_id`, `response_text_length` |

**Sin cambio de schema ni Terraform.** El array acepta cualquier estructura de evento.

---

### 4. IAM — Sin cambios

Los permisos actuales del Task Role ya cubren las operaciones necesarias:

| Tabla | Acciones ya permitidas | Uso en UOW-04 |
|---|---|---|
| `ppai-tasks` | GetItem, PutItem, UpdateItem, Query | Leer/actualizar estado de tareas |
| `ppai-events` | PutItem, Query | Registrar InteractionEvents |
| `ppai-cycles` | GetItem, PutItem, UpdateItem, Query | Registrar eventos de interacción en ciclo |

---

### 5. ECS — Sin cambios de topología

UOW-04 corre dentro del mismo proceso del bot. Las nuevas funcionalidades son handlers de callback que ya están registrados en `python-telegram-bot`:

```text
ECS Task (ppai-bot)
├── python-telegram-bot (handlers reactivos)        ← ya existe
│   ├── MessageHandler (captura)                    ← UOW-01
│   ├── CommandHandler /top3                        ← UOW-02
│   ├── CommandHandler /config                      ← UOW-03 (v0.7.0)
│   ├── CallbackQueryHandler (done/snooze/clarify)  ← UOW-02 existente, UOW-04 extiende
│   └── MessageHandler (clarify response)           ← UOW-04 nuevo
└── NudgeScheduler (tick cada 15 min)               ← UOW-03
```

---

### 6. CloudWatch — Sin grupos nuevos

Nuevos patrones de log en el log group existente `/ppai/bot`:

| Evento | Nivel | Campos clave |
|---|---|---|
| `respond.done` | INFO | `user_id`, `task_id`, `from_status` |
| `respond.snooze` | INFO | `user_id`, `task_id`, `snooze_count`, `snoozed_until` |
| `respond.clarify` | INFO | `user_id`, `task_id` |
| `respond.clarify_resolved` | INFO | `user_id`, `task_id` |
| `respond.unauthorized` | WARN | `callback_user_id`, `task_user_id` |
| `respond.idempotent_skip` | INFO | `user_id`, `task_id`, `current_status` |
| `event.recording_failed` | WARN | `user_id`, `task_id`, `error` |

---

### 7. Networking — Sin cambios

No se requiere nuevo endpoint, VPC link ni regla de security group.

---

## Resumen del delta

| Área | Cambio |
|---|---|
| DynamoDB `ppai-events` | **Habilitar TTL** con atributo `ttl` (Terraform: 4 líneas) |
| DynamoDB `ppai-tasks` | **+2 atributos** `snoozedUntil`, `completedAt` (solo código, schemaless) |
| DynamoDB `ppai-cycles` | **+4 event types** en array existente (solo código) |
| IAM Task Role | Sin cambios |
| ECS | Sin cambios (nuevo handler en mismo proceso) |
| CloudWatch | Sin grupos nuevos (7 nuevos eventos en log existente) |
| Networking | Sin cambios |
| ECR | Sin cambios |

---

## Dependencias hacia recursos existentes

| Recurso existente | Uso desde UOW-04 |
|---|---|
| `ppai-tasks` (UOW-01) | Leer/actualizar estado con nuevos campos y transiciones |
| `ppai-events` (UOW-01) | Registrar InteractionEvents con TTL de 90 días |
| `ppai-cycles` (UOW-02) | Registrar eventos de interacción en ciclo diario |
| `ppai-preferences` (UOW-03) | Lectura de timezone para correlación de ciclos |
| DecisionService cache (UOW-02) | Invalidar al procesar callbacks |

---

## Security Compliance

| Regla | Estado | Nota |
|---|---|---|
| SECURITY-01 Encryption at rest | Compliant | Tablas existentes ya cifradas |
| SECURITY-03 No sensitive data | Compliant | InteractionEvents solo metadata operativa, sin texto de tareas |
| SECURITY-06 Least Privilege | Compliant | Permisos existentes suficientes, sin ampliación |
| SECURITY-08 Access Control | Compliant | Callback authorization validada en capa de servicio (BR-RSP-07) |
| SECURITY-11 Secure Design | Compliant | Mensajes genéricos en caso de auth failure, sin data leak |

---

## Terraform — Cambios requeridos

**Un solo cambio**: Agregar bloque TTL a la tabla `ppai-events` en `terraform/modules/dynamodb/main.tf`:

```hcl
ttl {
  attribute_name = "ttl"
  enabled        = true
}
```

Ningún otro cambio de Terraform necesario para UOW-04.
