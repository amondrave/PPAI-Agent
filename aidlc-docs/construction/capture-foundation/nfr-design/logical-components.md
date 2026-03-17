# Logical Components — UOW-01 Capture Foundation

## Component Diagram

```
                         EXTERNAL
                    +----------------+
                    |  Telegram API  |
                    +-------+--------+
                            |
                      HTTPS webhook POST
                            |
                    +-------v--------+
                    |      ALB       |  <-- TLS termination, access logs
                    | (Public subnet)|
                    +-------+--------+
                            |
                      HTTP forward (port 8443)
                            |
          PRIVATE SUBNET    |
          +-----------------v------------------+
          |         ECS Fargate Task           |
          |                                    |
          |  +------------------------------+  |
          |  |     Telegram Adapter (C1)     |  |
          |  |  - Webhook handler            |  |
          |  |  - Rate Limiter (in-memory)   |  |
          |  |  - Webhook secret validation  |  |
          |  +-------------+----------------+  |
          |                |                   |
          |                v                   |
          |  +------------------------------+  |
          |  |   Capture Service (C2)        |  |
          |  |  - Input validation           |  |
          |  |  - Multi-line parsing          |  |
          |  |  - Normalization              |  |
          |  |  - Tag/deadline extraction    |  |
          |  |  - Dedup check               |  |
          |  |  - Active task limit check   |  |
          |  |  - TaskState creation         |  |
          |  |  - Event emission (best effort)|  |
          |  +-------------+----------------+  |
          |                |                   |
          |     uses Ports (Protocols)         |
          |                |                   |
          |  +-------------v----------------+  |
          |  |     Repository Layer          |  |
          |  |  - DynamoDB Task Repo (C8)   |  |
          |  |  - DynamoDB Event Repo (C9)  |  |
          |  |  - DynamoDB Dedup Repo       |  |
          |  +-------------+----------------+  |
          |                |                   |
          +----------------+-------------------+
                           |
                    VPC Endpoint (Gateway)
                           |
                    +------v-------+
                    |   DynamoDB   |
                    |  - ppai-tasks |
                    |  - ppai-events|
                    |  - ppai-dedup |
                    +--------------+

          +-----------------------------+
          |     CloudWatch Logs         |
          |  - JSON structured logs     |
          |  - 90-day retention         |
          +-----------------------------+
```

### Text Alternative
1. Telegram API sends webhook POST to ALB (public subnet, TLS termination)
2. ALB forwards to ECS Fargate task (private subnet, port 8443)
3. Telegram Adapter receives request, validates webhook secret, applies rate limiter
4. Capture Service orchestrates: validate → parse → normalize → dedup → persist → confirm
5. Repository Layer implements DynamoDB operations via VPC Endpoint
6. Logs exported to CloudWatch via awslogs driver

---

## Component Details

### LC-01: Application Load Balancer (ALB)

| Attribute | Value |
|---|---|
| Location | Public subnet |
| Purpose | TLS termination, route webhook traffic to ECS task |
| Listener | HTTPS (443) with ACM certificate |
| Target Group | ECS Fargate task, port 8443, health check on `/health` |
| Access Logs | Enabled → S3 bucket (SECURITY-02) |
| Security Group | Inbound: 443 from Telegram IP ranges; Outbound: 8443 to ECS SG |

### LC-02: ECS Fargate Task

| Attribute | Value |
|---|---|
| Location | Private subnet |
| Image | `ppai-bot:X.Y.Z` (pinned tag, no latest) |
| CPU/Memory | 0.25 vCPU / 512 MB (mínimo Fargate, suficiente para MVP) |
| Port | 8443 (webhook server) |
| Health Check | HTTP GET `/health` → 200 OK |
| Restart Policy | ECS service `desiredCount=1`, restart on failure |
| Logging | awslogs driver → CloudWatch log group `/ppai/bot` |
| Environment | Variables de entorno para config (TELEGRAM_BOT_TOKEN, DYNAMODB_TABLE_PREFIX, etc.) |
| IAM Role | Task role con permisos mínimos (ver LC-06) |

### LC-03: DynamoDB Table — `ppai-tasks`

| Attribute | Value |
|---|---|
| Partition Key | `userId` (String) |
| Sort Key | `taskId` (String, UUID) |
| Capacity | On-Demand |
| Encryption | AWS managed keys (default) |
| GSI-1 | `userId-status-index` — PK: `userId`, SK: `status` |
| Purpose | Almacenar TaskState, queries de tareas activas por usuario |

### LC-04: DynamoDB Table — `ppai-events`

| Attribute | Value |
|---|---|
| Partition Key | `userId` (String) |
| Sort Key | `timestamp#eventId` (String, composite) |
| Capacity | On-Demand |
| Encryption | AWS managed keys (default) |
| Purpose | Almacenar CaptureEvent (best effort, append-only pattern) |

### LC-05: DynamoDB Table — `ppai-dedup`

| Attribute | Value |
|---|---|
| Partition Key | `userId#exactTextHash` (String, composite con SHA-256) |
| TTL Attribute | `expiresAt` (Number, epoch seconds) |
| Capacity | On-Demand |
| Encryption | AWS managed keys (default) |
| Purpose | Control de deduplicación con ventana de 5 minutos (auto-cleanup via TTL) |

### LC-06: IAM Task Role

| Permission | Resource | Justification |
|---|---|---|
| `dynamodb:PutItem` | `ppai-tasks`, `ppai-events`, `ppai-dedup` | Persist TaskState, events, dedup records |
| `dynamodb:GetItem` | `ppai-tasks`, `ppai-dedup` | Read task by ID, check dedup |
| `dynamodb:Query` | `ppai-tasks`, `ppai-tasks/index/*` | Count active tasks (GSI query) |
| `dynamodb:UpdateItem` | `ppai-tasks` | Update task status |
| `logs:CreateLogStream` | `/ppai/bot` log group | Create log streams |
| `logs:PutLogEvents` | `/ppai/bot` log group | Write log entries |

### LC-07: VPC Networking

| Component | Configuration |
|---|---|
| VPC | CIDR block dedicado para PPAI |
| Public Subnet | ALB, NAT Gateway |
| Private Subnet | ECS Fargate tasks |
| NAT Gateway | Outbound internet (Telegram API HTTPS) |
| VPC Endpoint | DynamoDB Gateway endpoint (sin tráfico internet) |
| Security Groups | ALB SG (inbound 443), ECS SG (inbound 8443 from ALB SG only) |

### LC-08: CloudWatch Logs

| Attribute | Value |
|---|---|
| Log Group | `/ppai/bot` |
| Retention | 90 days (SECURITY-14) |
| Format | JSON structured (structlog) |
| Fields | timestamp, correlationId, level, userId, stage, message |

### LC-09: Terraform State Backend

| Component | Configuration |
|---|---|
| State Storage | S3 bucket con versioning y encryption |
| State Locking | DynamoDB table para lock |
| Purpose | State remoto para gestión de infraestructura |

---

## Component Interaction Flow (Capture)

```
Telegram API
  |
  | POST /webhook/<secret>
  v
ALB (TLS termination)
  |
  | HTTP forward
  v
Telegram Adapter
  |
  |-- Rate Limit check (in-memory) --[REJECT if exceeded]--> Reply "Demasiados mensajes"
  |
  v
Capture Service
  |
  |-- 1. Validate input --[INVALID]--> Reply "No pude interpretar tu mensaje"
  |
  |-- 2. Parse lines (multi-task)
  |
  |-- 3. For each line:
  |     |-- 3a. Normalize
  |     |-- 3b. Extract tag/deadline
  |     |-- 3c. Dedup check --> DynamoDB (ppai-dedup) GetItem
  |     |     [DUPLICATE] --> skip, count
  |     |-- 3d. Active limit check --> DynamoDB (ppai-tasks) Query GSI
  |     |     [LIMIT] --> reject, Reply limit message
  |     |-- 3e. Create TaskState (captured -> pending)
  |     |-- 3f. Persist --> DynamoDB (ppai-tasks) PutItem
  |     |-- 3g. Emit CaptureEvent --> DynamoDB (ppai-events) PutItem [best effort]
  |     |-- 3h. Record dedup --> DynamoDB (ppai-dedup) PutItem [best effort]
  |
  |-- 4. Send confirmation --> Telegram API (via ALB outbound -> NAT -> internet)
  v
Done
```

---

## Terraform Module Mapping

| Terraform Module | Logical Components Covered |
|---|---|
| `modules/networking` | LC-07 (VPC, subnets, NAT, VPC endpoints, security groups) |
| `modules/dynamodb` | LC-03, LC-04, LC-05 (tables, GSIs, TTL config) |
| `modules/ecs` | LC-02 (cluster, task definition, service, health check) |
| `modules/alb` | LC-01 (ALB, listener, target group, ACM cert) |
| `modules/iam` | LC-06 (task role, policies) |
| `modules/monitoring` | LC-08 (CloudWatch log groups, retention) |
| `modules/terraform-backend` | LC-09 (S3 bucket, DynamoDB lock table) |
