# Tech Stack Decisions — UOW-01 Capture Foundation

## Runtime & Language

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.12+ | Preferencia del usuario. Ecosistema maduro para bots Telegram y AWS SDK |
| Runtime | CPython | Standard, bien soportado en contenedores |
| Package Manager | Poetry o pip con requirements.txt + lock | Pinned versions (SECURITY-10) |

## Frameworks & Libraries

| Component | Library | Rationale |
|---|---|---|
| Telegram Bot | python-telegram-bot (v20+) | Async, well-maintained, webhook support |
| HTTP Server (webhook) | Built-in de python-telegram-bot (or uvicorn + starlette si se necesita health check separado) | Mínima dependencia adicional |
| AWS SDK | boto3 | Standard para DynamoDB, IAM, CloudWatch |
| Logging | structlog | JSON structured logging, correlation IDs, Python-native |
| Validation | pydantic (v2) | Validación de input, serialización de entidades, type safety |
| Testing | pytest + pytest-asyncio + moto | Unit/integration/e2e, moto para mock de DynamoDB |
| Env/Config | pydantic-settings | Carga de env vars con defaults y validación |

## Data Store

| Decision | Choice | Rationale |
|---|---|---|
| Primary Store | AWS DynamoDB | Serverless, managed, escalable, alineado con despliegue AWS |
| Capacity Mode | On-Demand | Bajo volumen MVP, sin provisioning necesario |
| Encryption | AWS managed keys (default) | SECURITY-01 compliant sin configuración adicional |

### DynamoDB Table Design (UOW-01)

#### Table: `ppai-tasks`
- **Partition Key**: `userId` (String)
- **Sort Key**: `taskId` (String — UUID)
- **Attributes**: todos los campos de TaskState (originalText, normalizedText, tag, deadline, status, sourceIntentId, createdAt, updatedAt)
- **GSI-1**: `userId-status-index` — PK: `userId`, SK: `status` (para queries de tareas activas por usuario)

#### Table: `ppai-events`
- **Partition Key**: `userId` (String)
- **Sort Key**: `timestamp#eventId` (String — composite para orden cronológico)
- **Attributes**: eventType, taskId, originalText, correlationId

#### Table: `ppai-dedup`
- **Partition Key**: `userId#exactTextHash` (String — composite key con SHA-256 del texto exacto)
- **TTL attribute**: `expiresAt` (Number — epoch seconds, 5 minutos desde lastSeenAt)
- **Attributes**: taskId, lastSeenAt

## Infrastructure as Code

| Decision | Choice | Rationale |
|---|---|---|
| IaC Tool | **Terraform** | Toda la infraestructura AWS se define y gestiona via Terraform |
| State Backend | S3 + DynamoDB lock (o Terraform Cloud) | State remoto para consistencia y colaboración |
| Module Strategy | Módulos por recurso lógico (networking, ecs, dynamodb, monitoring) | Reutilización y claridad |
| Version Pinning | Provider versions pinned en `required_providers` | Reproducibilidad (SECURITY-10) |

### Terraform Scope for UOW-01
- VPC, subnets, NAT gateway, VPC endpoints
- DynamoDB tables (`ppai-tasks`, `ppai-events`, `ppai-dedup`)
- ECS cluster, task definition, service
- IAM roles y policies (task execution role, task role)
- CloudWatch log groups con retention policy
- Security groups

## Deployment

| Decision | Choice | Rationale |
|---|---|---|
| Platform | AWS ECS Fargate | Container managed, sin servidor que administrar, auto-restart |
| Container | Docker (Python 3.12-slim base) | Imagen ligera, reproducible |
| Task Count | 1 (single task) | Suficiente para 1-5 usuarios |
| Restart Policy | ECS service con `desiredCount=1`, restart on failure | Disponibilidad razonable sin HA compleja |
| Networking | VPC con private subnet + NAT gateway | SECURITY-07 compliant |
| DynamoDB Access | VPC Endpoint (Gateway type) | Sin tráfico por internet público |
| Provisioning | **Terraform** | Toda la infraestructura definida como código, sin recursos manuales |

## Observability

| Decision | Choice | Rationale |
|---|---|---|
| Log Destination | CloudWatch Logs | Integración nativa con ECS Fargate (awslogs driver) |
| Log Format | JSON structured (via structlog) | Parseable, queryable en CloudWatch Insights |
| Log Retention | 90 días | SECURITY-14 minimum |
| Metrics | CloudWatch custom metrics (vía boto3 o embedded metric format) | Sin infraestructura adicional |

## Secrets Management

| Secret | Dev Environment | Production |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `.env` file (gitignored) | ECS task definition env var (o SSM Parameter Store) |
| AWS credentials | AWS CLI profile / env vars | IAM Task Role (no access keys) |
| `DYNAMODB_TABLE_PREFIX` | `.env` file | ECS task definition env var |

## Testing Infrastructure

| Layer | Tool | Scope |
|---|---|---|
| Unit Tests | pytest | Normalización, validación, dedup logic, tag/deadline extraction |
| Integration Tests | pytest + moto | Flujo completo contra DynamoDB mock (moto) |
| E2E Tests | pytest + respuestas simuladas | Flujo contra Telegram API mock |
| Coverage | pytest-cov | Target: >80% en lógica de negocio |

## Dependency Pinning (SECURITY-10)

- Todas las dependencias con versión exacta en `requirements.txt` o `poetry.lock`
- Dockerfile usa imagen base con tag específico (e.g., `python:3.12.8-slim`), no `latest`
- Dependencia de vulnerability scanning: `pip-audit` o `safety` en CI/CD pipeline
