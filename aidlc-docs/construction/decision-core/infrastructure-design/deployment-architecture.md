# Deployment Architecture — UOW-02 Decision Core

## Diagrama de componentes (delta UOW-02)

```
Usuario Telegram
      |
      | HTTPS POST /webhook/{secret}
      v
[API Gateway HTTP API]          ← heredado UOW-01, sin cambios
      |
      | VPC Link
      v
[ECS Fargate Task]              ← mismo task, imagen actualizada con UOW-02
  ppai-bot-service (1 task)
  ┌─────────────────────────────────────────────────┐
  │  main.py (wiring)                               │
  │                                                 │
  │  capture/ (UOW-01)                              │
  │    TelegramAdapter ── CaptureService            │
  │                                                 │
  │  decision/ (UOW-02) ← NUEVO                     │
  │    DecisionTelegramAdapter                      │
  │      /top3 command handler                      │
  │      callback handler (done|snooze|clarify)     │
  │    DecisionService                              │
  │      Top3Cache (in-memory, 60s TTL)             │
  │    ScoringEngine (pure computation)             │
  └─────────────────────────────────────────────────┘
      |                    |
      | Query              | PutItem/UpdateItem
      v                    v
[DynamoDB]
  ppai-tasks              ← heredada UOW-01
    GSI: userId-status-index  ← ya existía, reutilizada
  ppai-events             ← heredada UOW-01
  ppai-dedup              ← heredada UOW-01
  ppai-cycles             ← NUEVA (UOW-02)
    GSI: userId-date-index
      |
      v
[CloudWatch Logs]
  /ppai/bot               ← heredado, nuevos eventos DEC-*
```

---

## Flujo de deploy (sin cambios respecto a UOW-01)

```
1. Desarrollador pushea código con UOW-02
2. GitHub Actions (Step 15 — pendiente UOW-01):
   - pytest + behave → tests en verde
   - docker build → imagen nueva
   - docker push → ECR ppai-bot:v0.2.0
3. Terraform (manual):
   - terraform plan → muestra: +ppai-cycles table, +IAM policy delta
   - terraform apply → crea recursos nuevos
4. ECS rolling update:
   - Nueva task definition con imagen v0.2.0
   - ECS reemplaza task existente (desiredCount=1, zero-downtime para 1 usuario)
```

---

## Entornos

Solo producción (heredado de UOW-01). No hay staging para MVP.

Desarrollo local:
- `.env` con `TELEGRAM_BOT_TOKEN` (ya configurado)
- `ppai/local.py` con polling mode (pendiente — UOW-01 LocalStack setup)
- Hasta que LocalStack esté disponible: tests con `moto` para DynamoDB mock

---

## Tabla de recursos AWS (acumulado UOW-01 + UOW-02)

| Recurso | Nombre | UOW |
|---|---|---|
| API Gateway HTTP API | `ppai-api` | UOW-01 |
| ECS Cluster | `ppai-cluster` | UOW-01 |
| ECS Service | `ppai-bot-service` | UOW-01 |
| ECR Repository | `ppai-bot` | UOW-01 |
| DynamoDB Table | `ppai-tasks` | UOW-01 |
| DynamoDB Table | `ppai-events` | UOW-01 |
| DynamoDB Table | `ppai-dedup` | UOW-01 |
| DynamoDB Table | `ppai-cycles` | **UOW-02** |
| IAM Task Execution Role | `ppai-task-execution-role` | UOW-01 |
| IAM Task Role | `ppai-task-role` | UOW-01 (extendido en UOW-02) |
| CloudWatch Log Group | `/ppai/bot` | UOW-01 |
| CloudWatch Log Group | `/ppai/apigw` | UOW-01 |
| S3 Bucket (TF state) | `ppai-terraform-state-*` | UOW-01 |
| VPC | `ppai-vpc` | UOW-01 |
