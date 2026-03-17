# Code Generation Plan — UOW-01 Capture Foundation

## Unit Context
- **Unit**: UOW-01 Capture Foundation
- **Stories**: US-01 (Captura de intención), US-02 (Normalización mínima)
- **Components**: C1 (Telegram Adapter), C2 (Capture & Normalization), C8 (Loop State Store), C9 (Event Log)
- **Stack**: Python 3.12, python-telegram-bot v20+, boto3, pydantic v2, structlog, pytest
- **Infrastructure**: API Gateway HTTP API, ECS Fargate, DynamoDB, ECR, Terraform
- **Architecture**: DDD package-per-feature (capture/ + shared/)
- **Workspace Root**: `/Users/angelmondragon/Desktop/PPAI/ppai`

## Code Location
- **Application code**: Workspace root (ppai/, tests/, terraform/, Dockerfile, etc.)
- **Documentation summaries**: aidlc-docs/construction/capture-foundation/code/

## Dependencies
- UOW-01 has no upstream dependencies (first unit)
- Downstream units (UOW-02..05) will depend on TaskState entity and shared infrastructure

---

## Generation Steps

### Step 1: Project Structure Setup
- [ ] Create root project files: `pyproject.toml` (Poetry), `.gitignore`, `Dockerfile`, `requirements.txt`
- [ ] Create DDD package structure:
  ```
  ppai/
    __init__.py
    capture/
      __init__.py
      domain/
        __init__.py
      application/
        __init__.py
      infrastructure/
        __init__.py
    shared/
      __init__.py
      domain/
        __init__.py
      infrastructure/
        __init__.py
    main.py
  tests/
    __init__.py
    unit/
      __init__.py
      capture/
        __init__.py
    integration/
      __init__.py
      capture/
        __init__.py
    e2e/
      __init__.py
    conftest.py
  ```
- [ ] Create `ppai/shared/infrastructure/config.py` (pydantic-settings: TELEGRAM_BOT_TOKEN, DYNAMODB_TABLE_PREFIX, ACTIVE_TASK_LIMIT, DEDUP_WINDOW_SECONDS, RATE_LIMIT_PER_MINUTE)
- **Stories**: Foundation for US-01, US-02

### Step 2: Domain Layer — Entities and Value Objects
- [ ] Create `ppai/capture/domain/value_objects.py`: TaskStatus enum (captured, pending, prioritized, nudged, done, snoozed, clarifying)
- [ ] Create `ppai/capture/domain/entities.py`: Intent, TaskState, CaptureEvent, DedupRecord dataclasses/pydantic models
- [ ] Create `ppai/capture/domain/exceptions.py`: InvalidInputError, DuplicateTaskError, TaskLimitReachedError, CaptureError
- [ ] Create `ppai/shared/domain/base_entity.py`: Base classes, UUID generation utility
- **Stories**: US-02 (normalización, estructura de entidades)

### Step 3: Domain Layer — Unit Tests
- [ ] Create `tests/unit/capture/test_entities.py`: Test TaskState creation, status transitions (captured→pending), field validation
- [ ] Create `tests/unit/capture/test_value_objects.py`: Test TaskStatus enum values and valid transitions
- **Stories**: US-02

### Step 4: Application Layer — Ports (Repository Interfaces)
- [ ] Create `ppai/capture/application/ports.py`: TaskStateRepository, EventRepository, DedupRepository (Python Protocols)
- **Stories**: US-01, US-02 (contracts for persistence)

### Step 5: Application Layer — Capture Service (Business Logic)
- [ ] Create `ppai/capture/application/capture_service.py`: CaptureService class with:
  - `process_message(user_id, text) -> CaptureResult`
  - `_validate_input(text) -> str` (BR-CAP-01)
  - `_parse_lines(text) -> list[str]` (BR-CAP-02)
  - `_normalize(line) -> tuple[str, str]` (BR-CAP-09, step 3a)
  - `_extract_tag_deadline(text) -> tuple[str, str|None, datetime|None]` (BR-CAP-03, BR-CAP-04)
  - `_check_dedup(user_id, exact_text) -> bool` (BR-CAP-05)
  - `_check_task_limit(user_id) -> bool` (BR-CAP-06)
  - `_create_task(user_id, original, normalized, tag, deadline, intent_id) -> TaskState` (BR-CAP-10)
  - `_build_confirmation(created, duplicated, limit_reached) -> str` (BR-CAP-07)
- **Stories**: US-01 (capture flow), US-02 (normalization + dedup)

### Step 6: Application Layer — Unit Tests
- [ ] Create `tests/unit/capture/test_capture_service.py`: Tests for:
  - Input validation (empty, whitespace, emojis-only → error)
  - Multi-line parsing (split, empty line filtering)
  - Normalization (trim, collapse spaces, preserve original)
  - Tag extraction (#trabajo → tag="trabajo", removed from normalized)
  - Deadline extraction ("para mañana", "hoy", "urgente", "para DD/MM")
  - Dedup detection (mock repo returning True/False)
  - Task limit check (mock repo returning count)
  - Confirmation messages (1 task, N tasks, duplicates, limit)
  - Full flow integration with mock repos
- **Stories**: US-01, US-02

### Step 7: Infrastructure Layer — DynamoDB Repositories
- [ ] Create `ppai/capture/infrastructure/dynamodb_task_repo.py`: DynamoDBTaskStateRepository implementing TaskStateRepository
  - `save(task)`: PutItem to ppai-tasks
  - `get_by_id(user_id, task_id)`: GetItem
  - `count_active(user_id)`: Query GSI userId-status-index, filter active statuses
- [ ] Create `ppai/capture/infrastructure/dynamodb_event_repo.py`: DynamoDBEventRepository implementing EventRepository
  - `append(event)`: PutItem to ppai-events
- [ ] Create `ppai/capture/infrastructure/dynamodb_dedup_repo.py`: DynamoDBDedupRepository implementing DedupRepository
  - `exists(user_id, exact_text)`: GetItem by userId#SHA256(exactText), check TTL
  - `record(user_id, exact_text, task_id)`: PutItem with TTL = now + 300s
- [ ] Create `ppai/shared/infrastructure/dynamodb_client.py`: boto3 DynamoDB client factory (table name resolution, region config)
- **Stories**: US-01, US-02

### Step 8: Infrastructure Layer — Integration Tests
- [ ] Create `tests/integration/capture/test_dynamodb_repos.py`: Tests with moto mock:
  - TaskStateRepository: save, get_by_id, count_active
  - EventRepository: append
  - DedupRepository: exists (not found), record + exists (found), TTL behavior
- [ ] Create `tests/conftest.py`: Shared fixtures (moto DynamoDB mock, table creation)
- **Stories**: US-01, US-02

### Step 9: Infrastructure Layer — Telegram Adapter
- [ ] Create `ppai/capture/infrastructure/telegram_adapter.py`: Telegram webhook handler
  - `message_handler(update, context)`: async handler, delegates to CaptureService (sync)
  - Webhook secret validation
  - Error handling (generic response to user on unhandled error)
- [ ] Create `ppai/shared/infrastructure/rate_limiter.py`: InMemoryRateLimiter class
  - `check(user_id) -> bool`: sliding window 10/min
  - `_cleanup()`: remove expired entries
- **Stories**: US-01 (receive message, send confirmation)

### Step 10: Infrastructure Layer — Logging
- [ ] Create `ppai/shared/infrastructure/logging.py`: structlog configuration
  - JSON output, timestamp, correlation_id, level, user_id, stage
  - No PII in logs
- **Stories**: Transversal (observability)

### Step 11: Application Entry Point
- [ ] Create `ppai/main.py`: Application wiring and startup
  - Initialize config (pydantic-settings)
  - Initialize DynamoDB client and repositories
  - Initialize CaptureService with repos
  - Initialize python-telegram-bot Application
  - Register message handler + error handler
  - Register webhook on startup
  - Run webhook server on port 8443
  - Health check endpoint (`/health` → 200 OK)
- **Stories**: US-01 (end-to-end flow)

### Step 12: E2E Tests
- [ ] Create `tests/e2e/test_telegram_flow.py`: End-to-end tests with:
  - Simulated Telegram update (mock HTTP POST to webhook)
  - Full flow: message → validate → normalize → persist → confirm
  - Error cases: empty message, duplicate, limit reached
  - Uses moto for DynamoDB + mock for Telegram API responses
- **Stories**: US-01, US-02

### Step 13: Dockerfile and Container Config
- [ ] Create `Dockerfile`: Multi-stage build
  - Base: `python:3.12.8-slim`
  - Install dependencies from requirements.txt
  - Copy application code
  - Run ppai.main
  - Health check: `CMD curl -f http://localhost:8443/health || exit 1`
- [ ] Create `.dockerignore`: Exclude tests, docs, terraform, .env, __pycache__
- **Stories**: Deployment support

### Step 14: Terraform Infrastructure
- [ ] Create `terraform/providers.tf`: AWS provider, backend config (S3 + DynamoDB lock)
- [ ] Create `terraform/variables.tf`: Input variables (region, image_tag, table_prefix, etc.)
- [ ] Create `terraform/outputs.tf`: Outputs (APIGW URL, ECR URI, ECS cluster)
- [ ] Create `terraform/main.tf`: Root module wiring
- [ ] Create `terraform/modules/networking/`: VPC, subnets, NAT, VPC endpoints, security groups
- [ ] Create `terraform/modules/api-gateway/`: HTTP API, route, VPC Link, integration, access logs
- [ ] Create `terraform/modules/ecs/`: Cluster, task definition, service
- [ ] Create `terraform/modules/dynamodb/`: 3 tables, GSIs, TTL config
- [ ] Create `terraform/modules/iam/`: Task execution role, task role, policies
- [ ] Create `terraform/modules/ecr/`: Repository, scanning, lifecycle policy
- [ ] Create `terraform/modules/monitoring/`: CloudWatch log groups, retention
- **Stories**: Infrastructure support

### Step 15: GitHub Actions Workflow
- [ ] Create `.github/workflows/build-push.yml`: Build, test, push to ECR
  - Trigger: push to main (paths: ppai/, Dockerfile, requirements.txt)
  - Steps: checkout, setup Python, run tests, build Docker, push to ECR (OIDC)
- **Stories**: Deployment automation

### Step 16: Documentation Summaries
- [ ] Create `aidlc-docs/construction/capture-foundation/code/code-generation-summary.md`: Summary of all generated code, file inventory, story coverage
- **Stories**: US-01, US-02 traceability

---

## Story Coverage Matrix

| Step | US-01 (Capture) | US-02 (Normalization) |
|---|---|---|
| Step 1: Project Setup | Foundation | Foundation |
| Step 2: Domain Entities | | AC: estructura interna |
| Step 3: Domain Tests | | AC: estructura interna |
| Step 4: Ports | Contract | Contract |
| Step 5: Capture Service | AC: capture flow | AC: normalización, dedup |
| Step 6: Service Tests | AC: validation, multi-capture | AC: dedup, normalize |
| Step 7: DynamoDB Repos | AC: persistence | AC: persistence |
| Step 8: Integration Tests | AC: full flow | AC: full flow |
| Step 9: Telegram Adapter | AC: receive + confirm | |
| Step 10: Logging | Observability | Observability |
| Step 11: Entry Point | AC: end-to-end | AC: end-to-end |
| Step 12: E2E Tests | AC: all ACs | AC: all ACs |
| Step 13: Dockerfile | Deploy | Deploy |
| Step 14: Terraform | Infra | Infra |
| Step 15: GitHub Actions | CI/CD | CI/CD |
| Step 16: Documentation | Traceability | Traceability |
