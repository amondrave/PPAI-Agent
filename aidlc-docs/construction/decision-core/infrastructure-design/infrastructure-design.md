# Infrastructure Design — UOW-02 Decision Core

## Resumen de decisiones

| Decisión | Elección |
|---|---|
| Infraestructura base | Heredada de UOW-01 sin cambios (VPC, ECS, ECR, APIGW, CloudWatch) |
| Nueva tabla DynamoDB | `ppai-cycles` para ExecutionCycle |
| GSI para tareas pending | `userId-status-index` existente (UOW-01) — no se crea GSI nuevo |
| IAM Task Role | Extendido con permisos sobre `ppai-cycles` |
| Cache Top 3 | In-process (no Redis) — sin nueva infraestructura |
| Behave (BDD runner) | Dependencia Python — sin infraestructura adicional |

---

## Decisión de infraestructura: GSI reutilizado de UOW-01

En NFR Requirements (Q1=B) se planificó crear `userId-createdAt-index`.
Al revisar la infraestructura de UOW-01, la tabla `ppai-tasks` ya tiene:

```
userId-status-index — PK: userId, SK: status
```

Este GSI es **más eficiente** para el query de UOW-02:
```python
# Query directo sin FilterExpression — O(resultado), no O(tabla)
table.query(
    IndexName="userId-status-index",
    KeyConditionExpression=Key("userId").eq(user_id) & Key("status").eq("pending"),
)
```

**Decisión**: Usar `userId-status-index` existente. No se crea `userId-createdAt-index`.
El tie-breaking por `createdAt` se hace en memoria después del query (volumen MVP es bajo).

---

## INFRA-DEC-01: Nueva tabla `ppai-cycles`

| Atributo | Valor |
|---|---|
| Nombre | `ppai-cycles` |
| PK | `cycleId` (S) |
| SK | — (no sort key en tabla principal) |
| GSI | `userId-date-index`: PK=`userId` (S), SK=`date` (S) |
| TTL | — (ciclos no expiran automáticamente) |
| Capacity | On-Demand |
| Encryption | AWS managed keys (default) |
| Deletion protection | Enabled |
| Point-in-time recovery | Disabled (MVP) |

**Patrón de acceso principal:**
```python
# Obtener ciclo activo de un usuario para hoy
table.query(
    IndexName="userId-date-index",
    KeyConditionExpression=Key("userId").eq(user_id) & Key("date").eq(today_str),
    FilterExpression=Attr("status").eq("active"),
    Limit=1,
)
```

---

## INFRA-DEC-02: `snoozeCount` en `ppai-tasks`

Campo nuevo en `TaskState`. DynamoDB es schemaless — no requiere cambio de infraestructura.
- Tareas existentes: `snoozeCount` ausente → tratado como `0` en código.
- Tareas nuevas desde UOW-04: `snoozeCount` se incrementa en cada snooze.
- UOW-02 solo lee este campo.

**Acción Terraform**: Ninguna. El campo no requiere GSI ni proyección especial.

---

## INFRA-DEC-03: IAM Task Role — permisos extendidos

Permisos nuevos sobre `ppai-cycles` añadidos al role existente:

| Permission | Resource |
|---|---|
| `dynamodb:PutItem` | `ppai-cycles` |
| `dynamodb:GetItem` | `ppai-cycles` |
| `dynamodb:UpdateItem` | `ppai-cycles` |
| `dynamodb:Query` | `ppai-cycles`, `ppai-cycles/index/*` |

Permisos existentes sobre `ppai-tasks` extendidos con el GSI:

| Permission | Resource |
|---|---|
| `dynamodb:Query` | `ppai-tasks/index/userId-status-index` ← ya existía, confirmar ARN |

---

## INFRA-DEC-04: Cache in-process (sin infraestructura)

El cache Top 3 (TTL 60s) es in-memory dentro del proceso ECS.
- Sin Redis, sin ElastiCache, sin DynamoDB cache entries.
- Costo adicional: $0.
- Se pierde al reiniciar el task — aceptable (recalcula en frío en < 500ms).

---

## Infraestructura heredada de UOW-01 (sin cambios)

| Componente | Recurso | Estado |
|---|---|---|
| API Gateway HTTP API | `ppai-api` | Sin cambios — mismo endpoint webhook |
| ECS Fargate Service | `ppai-bot-service` | Sin cambios — mismo task, mismo container |
| Amazon ECR | `ppai-bot` | Sin cambios — nueva imagen con código UOW-02 |
| VPC + Subnets + NAT | `10.0.0.0/16` | Sin cambios |
| VPC Endpoint DynamoDB | Gateway endpoint | Sin cambios — tráfico DynamoDB interno |
| CloudWatch Log Groups | `/ppai/bot`, `/ppai/apigw` | Sin cambios |
| Terraform State Backend | S3 + DynamoDB lock | Sin cambios |

---

## Estimación de costo delta (UOW-02)

| Item | Costo adicional/mes |
|---|---|
| `ppai-cycles` DynamoDB (On-Demand, bajo volumen) | ~$0.10 |
| Queries adicionales al GSI `userId-status-index` | ~$0.05 |
| **Total delta UOW-02** | **~$0.15/mes** |

**Total acumulado MVP (UOW-01 + UOW-02):** ~$43.15/mes

---

## Terraform — cambios requeridos

### Módulo `dynamodb/` (existente)
Añadir resource para `ppai-cycles`:
```hcl
resource "aws_dynamodb_table" "cycles" {
  name         = "${var.table_prefix}-cycles"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "cycleId"

  attribute {
    name = "cycleId"
    type = "S"
  }
  attribute {
    name = "userId"
    type = "S"
  }
  attribute {
    name = "date"
    type = "S"
  }

  global_secondary_index {
    name            = "userId-date-index"
    hash_key        = "userId"
    range_key       = "date"
    projection_type = "ALL"
  }

  server_side_encryption { enabled = true }
  deletion_protection_enabled = true

  tags = { Project = "ppai", Unit = "uow-02" }
}
```

### Módulo `iam/` (existente)
Añadir al policy del task role:
```hcl
# ppai-cycles permissions
{
  Effect   = "Allow"
  Action   = ["dynamodb:PutItem","dynamodb:GetItem","dynamodb:UpdateItem","dynamodb:Query"]
  Resource = [
    aws_dynamodb_table.cycles.arn,
    "${aws_dynamodb_table.cycles.arn}/index/*",
  ]
}
```

---

## Security Compliance (delta UOW-02)

| Rule | Status | Notas |
|---|---|---|
| SECURITY-01 Encryption | Compliant | `ppai-cycles` con server_side_encryption habilitado |
| SECURITY-06 Least Privilege | Compliant | Permisos específicos por tabla y GSI en IAM task role |
| SECURITY-07 Network Config | Compliant (heredado) | Sin cambios — DynamoDB via VPC endpoint |
| SECURITY-13 Integrity | Compliant | deletion_protection en `ppai-cycles`, On-Demand = no capacity errors |
