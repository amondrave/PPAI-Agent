# Deployment Architecture — UOW-03 Push & Scheduling

## Topología general (sin cambios respecto a UOW-02)

```
Internet
   |
Telegram API
   |
VPC (AWS)
   |
[ECS Fargate — ppai-bot task]
   |
   +-- python-telegram-bot (webhook / polling handlers)
   |       |
   |       +-- CaptureService        (UOW-01)
   |       +-- DecisionService       (UOW-02)
   |       +-- CallbackAuthGuard     (UOW-03 - validación dual-layer)
   |
   +-- NudgeScheduler (in-process, tick 15 min)   ← NUEVO UOW-03
           |
           +-- NudgeService
                   |
                   +-- DynamoDBPreferencesRepo  --> ppai-preferences (NUEVA)
                   +-- CycleEventRepo           --> ppai-cycles      (UOW-02)
                   +-- DynamoDBTaskRepo          --> ppai-tasks       (UOW-01)
                   +-- TelegramPushAdapter       --> Telegram API
```

---

## Recursos AWS por ambiente

### Producción (us-east-1)

| Recurso | ID/Nombre | Estado |
|---|---|---|
| ECS Cluster | `ppai-cluster` | Existente |
| ECS Service | `ppai-bot` | Existente |
| ECR Repo | `ppai-bot` | Existente |
| DynamoDB `ppai-tasks` | Existente (UOW-01) | — |
| DynamoDB `ppai-events` | Existente (UOW-01) | — |
| DynamoDB `ppai-dedup` | Existente (UOW-01) | — |
| DynamoDB `ppai-cycles` | Existente (UOW-02) | — |
| DynamoDB `ppai-preferences` | **NUEVA (UOW-03)** | Por crear |
| IAM Task Role | `ppai-task-role` | Existente (ampliar permisos) |
| CloudWatch Log Group | `/ppai/bot` | Existente |
| VPC / Subnets / NAT | Existente | — |

---

## Terraform — archivos afectados

| Archivo | Cambio |
|---|---|
| `terraform/modules/dynamodb/main.tf` | Agregar `resource "aws_dynamodb_table" "preferences"` |
| `terraform/modules/dynamodb/outputs.tf` | Agregar `output "preferences_table_arn"` |
| `terraform/modules/dynamodb/variables.tf` | Sin cambio (usa `var.table_prefix` ya existente) |
| `terraform/modules/iam/main.tf` | Agregar statement para `ppai-preferences` en Task Role |
| `terraform/modules/iam/variables.tf` | Agregar `var.preferences_table_arn` |
| `terraform/main.tf` | Pasar `preferences_table_arn` de dynamodb → iam |
| `terraform/outputs.tf` | Agregar `preferences_table_arn` si necesario para trazabilidad |

---

## Secuencia de deploy

```
1. terraform plan         # verificar delta: 1 tabla nueva + 1 IAM statement
2. terraform apply        # crear ppai-preferences, actualizar task role
3. docker build & push    # imagen con scheduler in-process
4. ECS deploy (rolling)   # despliegue sin downtime
5. Verificar logs         # confirmar primer tick y NUDGE_SCHEDULED / NUDGE_SENT
```

---

## Rollback

| Componente | Estrategia |
|---|---|
| ECS | Rolling update → revertir imagen anterior en consola ECS |
| `ppai-preferences` | Tabla vacía al inicio; no hay data crítica que restaurar en primeras horas |
| IAM | Terraform state → `terraform apply` con versión anterior |

---

## Localstack (testing local)

Igual que UOW-01/02. Agregar `ppai-preferences` a `docker-compose.yml` bootstrap:

```yaml
# En localstack init script
aws dynamodb create-table \
  --table-name ppai-preferences \
  --attribute-definitions AttributeName=userId,AttributeType=S \
  --key-schema AttributeName=userId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --endpoint-url http://localhost:4566
```

---

## Estimación de costo delta (UOW-03)

| Recurso | Costo estimado |
|---|---|
| `ppai-preferences` reads/writes | < $0.10/mes (MVP, <100 usuarios) |
| ECS compute | Sin cambio (scheduler in-process) |
| CloudWatch logs | Incremento mínimo (~$0.01/mes) |
| **Total delta** | **< $0.20/mes** |
