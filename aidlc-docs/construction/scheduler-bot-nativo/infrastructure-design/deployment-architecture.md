# Deployment Architecture — UOW-05 Scheduler Bot Nativo

> Sin cambios de topología. Solo delta de DynamoDB GSI e IAM.

---

## Arquitectura de deployment (sin cambios)

```text
Internet
   |
   v
API Gateway HTTP API (webhook)
   |
   v
VPC (us-east-1)
├── Public Subnet
│   └── NAT Gateway → Internet (outbound Telegram API)
└── Private Subnet
    └── ECS Fargate Service (ppai-bot, desiredCount=1)
        ├── python-telegram-bot handlers
        ├── NudgeScheduler (tick dinámico)     ← MODIFICADO
        ├── ZenSessionManager (memoria)         ← NUEVO
        ├── DailySummaryBuilder                 ← NUEVO
        └── RescueEvaluator                     ← NUEVO

DynamoDB (us-east-1)
├── ppai-tasks        ← +GSI userId-status-index (NUEVO)
├── ppai-cycles       ← sin cambios de schema
├── ppai-events       ← sin cambios
└── ppai-preferences  ← +6 atributos (schemaless)

CloudWatch
└── /ppai/bot         ← nuevos eventos DAILY_START/END, ZEN, RESCUE

ECR
└── ppai-bot          ← nueva imagen con código UOW-05
```

---

## Terraform modules afectados

| Módulo | Cambio |
|--------|--------|
| `terraform/modules/dynamodb/main.tf` | Agregar GSI `userId-status-index` a `ppai-tasks` |
| `terraform/modules/iam/main.tf` | Agregar `dynamodb:Query` sobre ARN del GSI |
| Todos los demás | Sin cambios |

---

## Deployment process (sin cambios)

1. `terraform plan` — verificar delta (GSI + IAM)
2. `terraform apply` — crear GSI (operación online, sin downtime)
3. Docker build + push a ECR
4. ECS rolling update (nueva task definition)
5. Verificar health check + logs de nuevos eventos
