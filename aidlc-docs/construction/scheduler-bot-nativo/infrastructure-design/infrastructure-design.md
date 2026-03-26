# Infrastructure Design — UOW-05 Scheduler Bot Nativo

> Todo el stack base (ECS Fargate, DynamoDB, ECR, VPC, CloudWatch, OIDC) se hereda
> de UOW-01/02/03/04. Este documento describe únicamente el **delta de infraestructura**
> introducido por UOW-05.

---

## Delta de infraestructura

### 1. GSI en tabla DynamoDB existente: `ppai-tasks`

| Atributo | Valor |
|---|---|
| Tabla | `${var.table_prefix}-tasks` (ya existe) |
| GSI nombre | `userId-status-index` |
| Partition key | `userId` (String) |
| Sort key | `status` (String) |
| Proyección | `INCLUDE` — atributos: `title`, `completedAt`, `snoozedUntil` |
| Billing | Hereda PAY_PER_REQUEST de la tabla |
| Cifrado | Hereda SSE de la tabla |

**Access patterns del GSI:**
- `Query(userId=X, status=completed)` — tareas completadas para resumen de cierre
- `Query(userId=X, status=pending)` — tareas pendientes para resumen de cierre
- `Query(userId=X, status=snoozed)` — tareas pospuestas para resumen de cierre

**Terraform:**
```hcl
# En módulo dynamodb, recurso ppai-tasks
global_secondary_index {
  name               = "userId-status-index"
  hash_key           = "userId"
  range_key          = "status"
  projection_type    = "INCLUDE"
  non_key_attributes = ["title", "completedAt", "snoozedUntil"]
}
```

**Nota**: Agregar GSI a tabla existente en DynamoDB on-demand es una operación online, sin downtime.

---

### 2. Tabla `ppai-preferences` — atributos nuevos (sin cambio de schema)

DynamoDB es schemaless. Los 6 atributos nuevos se escriben directamente sin modificación de Terraform:

| Atributo DynamoDB | Tipo | Usado por |
|---|---|---|
| `dailyStartTime` | S | Recordatorio matutino |
| `dailyEndTime` | S | Resumen de cierre |
| `zenActive` | BOOL | Estado zen |
| `zenIntervalMinutes` | N | Intervalo zen |
| `zenMaxNudges` | N | Cap zen |
| `motivationalMessage` | S | Mensaje motivacional |

**No requiere cambio Terraform** — solo código de serialización en `DynamoDBPreferencesRepository`.

---

### 3. IAM — Task Role update

Agregar permiso de Query sobre el GSI al `ppai-task-role` existente:

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:Query"
  ],
  "Resource": "<tasks_table_arn>/index/userId-status-index"
}
```

**Acciones justificadas:**
- `Query` — consultar GSI para resumen de cierre (DailySummaryBuilder)

**Scope**: Solo el índice, no la tabla completa. Los permisos existentes sobre la tabla base (GetItem, PutItem, UpdateItem) no cambian.

---

### 4. ECS — Sin cambios de topología

El scheduler dinámico corre **in-process** dentro del mismo contenedor:

```text
ECS Task (ppai-bot)
├── python-telegram-bot (handlers reactivos)     ← ya existe
├── NudgeScheduler (tick dinámico 5-15 min)       ← modificado (era fijo 15 min)
├── ZenSessionManager (en memoria)                ← nuevo, mismo proceso
├── DailySummaryBuilder (consulta GSI)            ← nuevo, mismo proceso
└── RescueEvaluator (lógica pura)                 ← nuevo, mismo proceso
```

No se introduce:
- Nuevo servicio ECS ni tarea separada
- EventBridge Scheduler
- Lambda
- SQS / cola adicional

---

### 5. CloudWatch — Sin grupos nuevos

Los logs de UOW-05 usan el log group existente `/ppai/bot`.

Nuevos patrones de log (misma estructura structlog JSON):

| Evento | Nivel | Campos clave |
|---|---|---|
| `DAILY_START_SENT` | INFO | `user_id`, `cycle_id`, `sent_at` |
| `DAILY_END_SENT` | INFO | `user_id`, `cycle_id`, `sent_at`, `rescue_triggered` |
| `ZEN_ACTIVATED` | INFO | `user_id`, `interval_minutes`, `max_nudges` |
| `ZEN_DEACTIVATED` | INFO | `user_id`, `nudges_sent`, `reason` (manual/auto) |
| `RESCUE_TRIGGERED` | INFO | `user_id`, `cycle_id`, `task_id` |

---

### 6. Networking — Sin cambios

Sin nuevos endpoints, VPC links ni reglas de security group.

---

## Resumen del delta

| Área | Cambio | Terraform |
|---|---|---|
| DynamoDB `ppai-tasks` | **+1 GSI** `userId-status-index` | Sí |
| DynamoDB `ppai-preferences` | +6 atributos (schemaless, no Terraform) | No |
| IAM Task Role | **+Query** sobre GSI | Sí |
| ECS | Sin cambios de topología | No |
| CloudWatch | Nuevos eventos en log group existente | No |
| Networking | Sin cambios | No |
| ECR | Sin cambios | No |

---

## Dependencias hacia recursos existentes

| Recurso existente | Uso desde UOW-05 |
|---|---|
| `ppai-tasks` (UOW-01) | GSI para consulta de tareas por estado |
| `ppai-preferences` (UOW-03) | Nuevos atributos de scheduler/zen |
| `ppai-cycles` (UOW-02) | Eventos de inicio/cierre/zen/rescue |
| `/ppai/bot` (CloudWatch) | Log de nuevos eventos |

---

## Security Compliance

| Regla | Estado | Nota |
|---|---|---|
| SECURITY-01 Encryption at rest | Compliant | GSI hereda SSE de tabla ppai-tasks |
| SECURITY-06 Least Privilege | Compliant | Solo Query sobre GSI específico, no tabla completa |
| SECURITY-05 Input Validation | Compliant | Sanitización de motivational_message (DP-SCHED-07) |
| SECURITY-11 Secure Design | Compliant | Sin infra nueva pesada, scheduler dinámico con floor |
