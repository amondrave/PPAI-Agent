# Infrastructure Design — UOW-01 Capture Foundation

## Infrastructure Decisions Summary

| Decision | Choice |
|---|---|
| AWS Region | us-east-1 (N. Virginia) |
| Webhook Frontal | API Gateway (HTTP API) — reemplaza ALB del NFR Design |
| Environments | Solo producción |
| Container Registry | Amazon ECR |
| Deployment | Semi-automático (GitHub Actions build+push, terraform apply manual) |
| IaC | Terraform con state remoto en S3 |

## Architecture Change: API Gateway replaces ALB

El NFR Design (logical-components.md) definió un ALB como frontal. La decisión de infraestructura lo reemplaza por **API Gateway HTTP API**, lo cual simplifica la arquitectura:

| Aspecto | ALB (original) | API Gateway HTTP API (final) |
|---|---|---|
| TLS | ACM certificate + dominio custom | Automático (URL generada por APIGW) |
| Costo | ALB hourly + LCU | Pay-per-request (prácticamente gratis para MVP) |
| Access Logs | S3 bucket | CloudWatch Logs (SECURITY-02) |
| Config | Listener, target group, health check | Route + integration, más simple |
| Dominio | Requiere dominio custom | URL generada: `https://<api-id>.execute-api.us-east-1.amazonaws.com` |

### Impacto en Componentes Lógicos
- **LC-01 (ALB)** → reemplazado por **API Gateway HTTP API**
- **LC-07 (VPC Networking)** → simplificado: API Gateway invoca ECS via VPC Link (o via Cloud Map)
- Resto de componentes sin cambio

---

## AWS Service Mapping

### INFRA-01: API Gateway HTTP API

| Attribute | Value |
|---|---|
| Service | Amazon API Gateway (HTTP API, v2) |
| Purpose | Webhook endpoint público para Telegram, TLS automático |
| Route | `POST /webhook/{secret}` |
| Integration | VPC Link → ECS Fargate (private subnet) |
| Access Logging | Enabled → CloudWatch Logs (SECURITY-02) |
| Throttling | Default APIGW throttling + rate limiter in-app |
| Cost | $1.00/million requests — negligible para MVP |

### INFRA-02: ECS Fargate Service

| Attribute | Value |
|---|---|
| Service | Amazon ECS with Fargate launch type |
| Cluster | `ppai-cluster` |
| Service | `ppai-bot-service` (desiredCount=1) |
| Task Definition | `ppai-bot-task` |
| CPU/Memory | 0.25 vCPU / 512 MB |
| Port | 8443 (webhook server interno) |
| Health Check | Container health check via ECS |
| Networking | Private subnet, security group allows inbound from VPC Link |
| Logging | awslogs driver → CloudWatch log group `/ppai/bot` |
| Restart | ECS service maintains desired count, auto-replaces failed tasks |

### INFRA-03: DynamoDB Tables

| Table | PK | SK | GSI | TTL | Capacity |
|---|---|---|---|---|---|
| `ppai-tasks` | `userId` (S) | `taskId` (S) | `userId-status-index` (PK: userId, SK: status) | — | On-Demand |
| `ppai-events` | `userId` (S) | `timestamp#eventId` (S) | — | — | On-Demand |
| `ppai-dedup` | `userId#exactTextHash` (S) | — | — | `expiresAt` | On-Demand |

- Encryption at rest: AWS managed keys (default, SECURITY-01)
- Point-in-time recovery: Disabled para MVP (puede habilitarse después)
- All tables con deletion protection enabled

### INFRA-04: Amazon ECR

| Attribute | Value |
|---|---|
| Repository | `ppai-bot` |
| Image Scanning | Enabled on push (vulnerability detection) |
| Lifecycle Policy | Keep last 10 images, expire untagged after 7 days |
| Encryption | AES-256 (default) |
| Image Tag | Semantic versioning (e.g., `v0.1.0`), no `latest` in production |

### INFRA-05: IAM Roles

#### ECS Task Execution Role
| Permission | Resource |
|---|---|
| `ecr:GetAuthorizationToken` | `*` (required) |
| `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer` | `ppai-bot` repository |
| `logs:CreateLogStream`, `logs:PutLogEvents` | `/ppai/bot` log group |

#### ECS Task Role (application permissions)
| Permission | Resource |
|---|---|
| `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem`, `dynamodb:Query` | `ppai-tasks`, `ppai-tasks/index/*` |
| `dynamodb:PutItem` | `ppai-events` |
| `dynamodb:PutItem`, `dynamodb:GetItem` | `ppai-dedup` |

### INFRA-06: VPC Networking

| Component | Configuration |
|---|---|
| VPC | `10.0.0.0/16` |
| Public Subnet (AZ-a) | `10.0.1.0/24` — NAT Gateway |
| Public Subnet (AZ-b) | `10.0.2.0/24` — NAT Gateway (redundancy for APIGW VPC Link) |
| Private Subnet (AZ-a) | `10.0.10.0/24` — ECS Fargate tasks |
| Private Subnet (AZ-b) | `10.0.11.0/24` — ECS Fargate tasks (required by ECS) |
| NAT Gateway | 1x (single NAT for MVP cost savings) — outbound to Telegram API |
| VPC Endpoint (Gateway) | DynamoDB — sin tráfico internet para DB access |
| VPC Link | API Gateway → private subnets (ECS) |
| Security Group (ECS) | Inbound: port 8443 from VPC Link; Outbound: 443 to NAT + VPC endpoints |

### INFRA-07: CloudWatch

| Resource | Configuration |
|---|---|
| Log Group `/ppai/bot` | Retention: 90 days, application logs |
| Log Group `/ppai/apigw` | Retention: 90 days, API Gateway access logs |
| Metrics | Custom metrics via embedded metric format in application logs |

### INFRA-08: Terraform State Backend

| Component | Resource |
|---|---|
| State Bucket | S3 bucket `ppai-terraform-state-<account-id>` with versioning + encryption |
| Lock Table | DynamoDB table `ppai-terraform-lock` |
| Region | us-east-1 (same as deployment) |

---

## Cost Estimate (MVP — 1-5 users)

| Service | Estimated Monthly Cost |
|---|---|
| ECS Fargate (0.25 vCPU, 512MB, 24/7) | ~$9.50 |
| NAT Gateway (1x, low traffic) | ~$32.00 |
| DynamoDB (On-Demand, very low volume) | ~$0.50 |
| API Gateway (< 100K requests/month) | ~$0.10 |
| ECR (< 1 GB storage) | ~$0.10 |
| CloudWatch Logs (< 1 GB/month) | ~$0.50 |
| S3 (Terraform state) | ~$0.01 |
| **Total Estimated** | **~$43/month** |

**Note**: El NAT Gateway es el costo dominante. Si el costo es una preocupación futura, se podría reemplazar por un NAT instance (t3.nano ~$3.50/month) o explorar alternativas sin VPC.

---

## Security Compliance Summary (Baseline Extension)

| Rule | Status | Notes |
|---|---|---|
| SECURITY-01 Encryption | Compliant | DynamoDB + ECR encryption at rest, TLS in transit everywhere |
| SECURITY-02 Access Logging | Compliant | API Gateway access logs → CloudWatch (replaces ALB logs) |
| SECURITY-03 App Logging | Compliant | structlog JSON → CloudWatch, 90-day retention |
| SECURITY-04 HTTP Headers | N/A | No HTML endpoints, Telegram bot only |
| SECURITY-05 Input Validation | Compliant | Validated in app layer + APIGW payload size limits |
| SECURITY-06 Least Privilege | Compliant | Separate execution role + task role, specific resources |
| SECURITY-07 Network Config | Compliant | Private subnets, VPC endpoints, NAT for outbound only |
| SECURITY-08 App Access Control | Compliant | Webhook secret validation, userId isolation |
| SECURITY-09 Hardening | Compliant | No default creds, ECR image scanning, pinned versions |
| SECURITY-10 Supply Chain | Compliant | ECR scanning on push, pinned image tags, lock files |
| SECURITY-11 Secure Design | Compliant | Rate limiting, layered architecture, separation of concerns |
| SECURITY-12 Auth & Credentials | N/A | No user passwords/sessions |
| SECURITY-13 Integrity | Compliant | ECR image immutable tags, auditable data changes |
| SECURITY-14 Alerting & Monitoring | Compliant | CloudWatch logs 90-day retention, access logs enabled |
| SECURITY-15 Exception Handling | Compliant | Global error handler, fail closed, APIGW default 5xx |
