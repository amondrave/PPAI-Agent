# Infrastructure Design — UOW-03 Push & Scheduling

> Todo el stack base (ECS Fargate, DynamoDB, ECR, VPC, CloudWatch, OIDC) se hereda
> de UOW-01/UOW-02. Este documento describe únicamente el **delta de infraestructura**
> introducido por UOW-03.

---

## Delta de infraestructura

### 1. Nueva tabla DynamoDB: `ppai-preferences`

| Atributo | Valor |
|---|---|
| Nombre | `${var.table_prefix}-preferences` |
| Billing | PAY_PER_REQUEST |
| PK | `userId` (String) |
| SK | Ninguna |
| GSI | Ninguno (MVP — acceso único por PK) |
| Cifrado | `server_side_encryption { enabled = true }` |
| Deletion protection | `true` |
| TTL | No aplica (datos de preferencias sin expiración) |

**Schema lógico de ítems:**

| Campo | Tipo DynamoDB | Obligatorio | Default |
|---|---|---|---|
| `userId` | S (PK) | Sí | — |
| `timezone` | S | No | `America/Bogota` |
| `maxNudgesPerDay` | N | No | `3` |
| `silenceStart` | S | No | null |
| `silenceEnd` | S | No | null |
| `updatedAt` | S (ISO 8601) | Sí | — |

**Access patterns:**
- `GetItem(userId)` — cargar preferencias del usuario al evaluar tick
- `PutItem(userId, ...)` — crear/actualizar preferencias (futuro `/config`)

---

### 2. IAM — Task Role update

Agregar statement al `ppai-task-role` existente:

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem"
  ],
  "Resource": "<preferences_table_arn>"
}
```

**Acciones justificadas:**
- `GetItem` — leer preferencias en cada tick del scheduler
- `PutItem` — crear preferencias con defaults si no existen
- `UpdateItem` — actualizar preferencias vía `/config` (futuro)

**No se necesitan:**
- `Query` (sin GSI, no hay scan por filtro)
- `DeleteItem` (las preferencias no se borran en MVP)
- Permisos sobre índices (sin GSI)

---

### 3. ECS — Sin cambios de topología

El scheduler corre **in-process** dentro del mismo contenedor del bot:

```text
ECS Task (ppai-bot)
├── python-telegram-bot (handlers reactivos)  ← ya existe
└── NudgeScheduler (tick cada 15 min)         ← nuevo, mismo proceso
```

No se introduce:
- Nuevo servicio ECS ni tarea separada
- EventBridge Scheduler
- Lambda
- SQS / cola adicional

---

### 4. CloudWatch — Sin grupos nuevos

Los logs del scheduler usan el log group existente `/ppai/bot`.

Nuevos patrones de log (misma estructura structlog JSON):

| Evento | Nivel | Campos clave |
|---|---|---|
| `NUDGE_SCHEDULED` | INFO | `cycle_id`, `task_id`, `window_start`, `window_end` |
| `NUDGE_SENT` | INFO | `cycle_id`, `task_id`, `sent_at` |
| `NUDGE_SKIPPED_ACTIVITY` | INFO | `cycle_id`, `reason`, `last_activity_at` |
| `NUDGE_FAILED` | ERROR | `cycle_id`, `task_id`, `attempt_count`, `error` |

---

### 5. Networking — Sin cambios

El scheduler envía a Telegram sobre la misma ruta de salida ya operativa (ECS → NAT → internet).
No se requiere nuevo endpoint, VPC link ni regla de security group.

---

## Resumen del delta

| Área | Cambio |
|---|---|
| DynamoDB | **Nueva tabla** `ppai-preferences` (PK: userId) |
| IAM Task Role | **+3 acciones** GetItem/PutItem/UpdateItem sobre `ppai-preferences` |
| ECS | Sin cambios |
| CloudWatch | Sin grupos nuevos (nuevos eventos en log group existente) |
| Networking | Sin cambios |
| ECR | Sin cambios |

---

## Dependencias hacia recursos existentes

| Recurso existente | Uso desde UOW-03 |
|---|---|
| `ppai-cycles` (UOW-02) | Leer ciclo activo, registrar eventos de dispatch |
| `ppai-tasks` (UOW-01) | Leer TaskState, actualizar status a `nudged` |
| `/ppai/bot` (CloudWatch) | Log de eventos del scheduler |

---

## Security Compliance

| Regla | Estado | Nota |
|---|---|---|
| SECURITY-01 Encryption at rest | Compliant | `ppai-preferences` con SSE habilitado |
| SECURITY-06 Least Privilege | Compliant | Solo GetItem/PutItem/UpdateItem, sin Query ni DeleteItem |
| SECURITY-08 Access Control | Compliant | Dual-layer auth en callbacks de nudge (DP-PUSH-07) |
| SECURITY-11 Secure Design | Compliant | Scheduler lean, sin infra extra, fail-soft |
