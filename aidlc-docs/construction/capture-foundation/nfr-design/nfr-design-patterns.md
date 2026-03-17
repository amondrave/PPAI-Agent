# NFR Design Patterns — UOW-01 Capture Foundation

## DP-01: Webhook Ingress Pattern

### Pattern
El bot recibe mensajes de Telegram via **webhook** (push model). Telegram envía un HTTP POST a un endpoint HTTPS del bot por cada update.

### Design
- python-telegram-bot v20+ expone un webhook server vía su clase `Application`
- El endpoint webhook requiere URL pública con TLS (HTTPS)
- En ECS Fargate: el contenedor corre un HTTP server (integrado en python-telegram-bot) que escucha en un puerto interno
- Un **Application Load Balancer (ALB)** con TLS termination expone el endpoint público
- Telegram envía updates a `https://<domain>/webhook/<bot-token-hash>`
- El path incluye un hash del token (no el token completo) como secret para validar que los requests vienen de Telegram

### Resilience
- Si el bot está caído, Telegram reintenta el webhook con backoff exponencial (hasta ~24h)
- Si el webhook falla repetidamente, Telegram desactiva el webhook — se necesita re-registrar al restart
- El bot re-registra el webhook al iniciar (idempotente)

### Security (SECURITY-02, SECURITY-05)
- ALB access logs habilitados (SECURITY-02)
- Validación del secret token en el path del webhook
- Solo aceptar requests POST con content-type application/json

---

## DP-02: DDD Package-per-Feature Structure

### Pattern
Arquitectura **package por feature orientada a DDD**. Cada bounded context es un paquete Python independiente con sus propias capas internas.

### Project Structure
```
ppai/
  capture/                    # Bounded Context: Capture (UOW-01)
    domain/
      entities.py             # Intent, TaskState, CaptureEvent, DedupRecord
      value_objects.py        # TaskStatus enum, tag, deadline
      exceptions.py           # Domain exceptions
    application/
      capture_service.py      # Orchestrates capture flow (use case)
      ports.py                # Repository interfaces (protocols)
    infrastructure/
      telegram_adapter.py     # Inbound adapter: Telegram webhook handler
      dynamodb_task_repo.py   # TaskStateRepository implementation
      dynamodb_event_repo.py  # EventRepository implementation
      dynamodb_dedup_repo.py  # DedupRecordRepository implementation
    __init__.py
  shared/                     # Shared Kernel
    domain/
      base_entity.py          # Base classes, common types
    infrastructure/
      dynamodb_client.py      # DynamoDB client factory/config
      logging.py              # Structured logging setup (structlog)
      config.py               # App configuration (pydantic-settings)
      rate_limiter.py         # In-memory rate limiter
  main.py                     # Application entry point, wiring
  __init__.py
tests/
  unit/
    capture/
      test_capture_service.py
      test_entities.py
      test_normalization.py
  integration/
    capture/
      test_dynamodb_repos.py
  e2e/
    test_telegram_flow.py
terraform/                    # Infrastructure as Code
  modules/
  environments/
  main.tf
```

### DDD Principles Applied
- **Entities** en `domain/`: lógica de negocio pura, sin dependencias de infraestructura
- **Ports** en `application/ports.py`: interfaces (Python Protocols) para repositories — inversión de dependencias
- **Adapters** en `infrastructure/`: implementaciones concretas de ports (DynamoDB, Telegram)
- **Application Service** en `application/`: orquesta el flujo de captura, depende solo de ports
- **Shared Kernel** en `shared/`: código común reutilizable entre bounded contexts (futuras UOWs)

### Extensibility
- Cada UOW futura (decision/, push/, respond/, learn/) será un paquete paralelo a `capture/`
- `shared/` crece incrementalmente con lo que se reutiliza
- Los ports permiten swap de implementación (ej: cambiar DynamoDB por otro store sin tocar domain/application)

---

## DP-03: Synchronous Processing with Async Framework

### Pattern
python-telegram-bot v20+ es **async-native** (requiere `async def` handlers). Sin embargo, la lógica de negocio y las llamadas a DynamoDB (boto3) son **síncronas**.

### Design
- Los handlers de Telegram son `async def` (requerido por el framework)
- Dentro de los handlers, las llamadas a boto3 (DynamoDB) se ejecutan **síncronamente directas**
- Justificación: para 1-5 usuarios con latencia DynamoDB <200ms, no hay beneficio real de async I/O
- Si en el futuro se necesita escalar, se puede migrar a `aiobotocore` sin cambiar la capa domain/application

### Example Pattern
```python
async def handle_message(update, context):
    # Framework requiere async, pero la lógica interna es sync
    result = capture_service.process_message(
        user_id=str(update.effective_user.id),
        text=update.message.text
    )
    await update.message.reply_text(result.confirmation_message)
```

### Trade-offs
- **Pro**: Código de negocio simple, fácil de testear, sin complejidad async
- **Pro**: boto3 es maduro y bien documentado en modo sync
- **Con**: Bloquea el event loop durante DynamoDB calls (~50-200ms) — aceptable para volumen MVP
- **Mitigation**: Si latencia es problema futuro, wrappear con `asyncio.to_thread()`

---

## DP-04: In-Memory Rate Limiter

### Pattern
Rate limiting con **sliding window counter en memoria** del proceso Python.

### Design
- Dict `{user_id: [timestamp1, timestamp2, ...]}` con timestamps de últimos mensajes
- Al recibir mensaje: filtrar timestamps > 60s, contar restantes
- Si count >= 10: rechazar con mensaje fijo, no procesar
- Se ejecuta **antes** de cualquier lógica de negocio o I/O (fail fast)

### Characteristics
- Se resetea al reiniciar el contenedor (aceptable para MVP personal)
- Sin overhead de I/O adicional (no DynamoDB read/write)
- Limpieza periódica de entries antiguas para evitar memory leak (cada N requests o timer)

### Implementation Location
- `shared/infrastructure/rate_limiter.py`
- Invocado en `capture/infrastructure/telegram_adapter.py` antes de delegar al service

---

## DP-05: Best-Effort Event Emission

### Pattern
Eventos de captura (CaptureEvent) se emiten como **side-effect best-effort** después de la operación principal.

### Design
- El flujo principal es: validate → normalize → dedup check → persist TaskState → confirm user
- **Después** de persistir TaskState exitosamente, se intenta escribir CaptureEvent
- Si CaptureEvent write falla: log warning, la captura ya es exitosa
- TaskState es la fuente de verdad, CaptureEvent es complementario

### Sequence
```
1. Validate input
2. Normalize + extract tags/deadline
3. Check dedup (DynamoDB GetItem)
4. Check active task limit (DynamoDB Query)
5. Persist TaskState (DynamoDB PutItem) ← critical path
6. Send confirmation to user (Telegram API) ← critical path
7. Emit CaptureEvent (DynamoDB PutItem) ← best effort
8. Record DedupRecord (DynamoDB PutItem) ← best effort
```

### Error Isolation
- Steps 5-6: si fallan, retornar error al usuario
- Steps 7-8: si fallan, log warning, no afectan al usuario
- Cada step tiene su propio try/except (SECURITY-15)

---

## DP-06: Repository Port Pattern (Dependency Inversion)

### Pattern
**Ports & Adapters** — los repositories se definen como Python Protocols en la capa application, implementados en infrastructure.

### Design
```python
# capture/application/ports.py
from typing import Protocol

class TaskStateRepository(Protocol):
    def save(self, task: TaskState) -> None: ...
    def get_by_id(self, user_id: str, task_id: str) -> TaskState | None: ...
    def count_active(self, user_id: str) -> int: ...

class EventRepository(Protocol):
    def append(self, event: CaptureEvent) -> None: ...

class DedupRepository(Protocol):
    def exists(self, user_id: str, exact_text: str) -> bool: ...
    def record(self, user_id: str, exact_text: str, task_id: str) -> None: ...
```

### Benefits
- Domain y application layer no importan boto3 ni DynamoDB
- Unit tests usan fakes/mocks de los Protocols
- Integration tests usan implementaciones reales con moto
- Swap de storage no requiere cambios en lógica de negocio

---

## DP-07: Structured Logging with Correlation

### Pattern
**Structured JSON logging** con correlation ID por request para trazabilidad end-to-end.

### Design
- structlog configurado en `shared/infrastructure/logging.py`
- Cada request de Telegram genera un `correlation_id` (UUID) al inicio del handler
- El correlation_id se propaga a todas las operaciones del flujo (bind en structlog context)
- Campos estándar: timestamp, correlation_id, level, user_id, stage, message

### Security (SECURITY-03)
- **No loggear**: rawText, originalText, normalizedText (PII potencial)
- **Sí loggear**: taskId, userId (numérico de Telegram), eventType, status, latencia
- Bot token nunca en logs
- Error messages genéricos en logs (no stack traces en producción para campos expuestos al usuario)

---

## DP-08: Global Error Handler (Fail Closed)

### Pattern
**Global error handler** que captura excepciones no manejadas y retorna respuesta segura al usuario.

### Design
- python-telegram-bot provee `Application.add_error_handler()` para capturar errores no manejados
- El error handler: log error con correlation_id + retornar mensaje genérico al usuario
- Mensaje al usuario: "Ocurrió un error procesando tu mensaje. Intenta de nuevo."
- **Fail closed**: en caso de error no manejado, no se persiste nada, no se emite evento

### Security (SECURITY-09, SECURITY-15)
- No exponer stack traces, paths internos ni detalles de DB al usuario
- Log interno sí incluye exception type y message para debugging
- Resources cleanup: boto3 client connections son managed (no requieren cleanup manual)

---

## Security Compliance Summary (Baseline Extension)

| Rule | Status | Notes |
|---|---|---|
| SECURITY-01 Encryption | Compliant | DynamoDB encryption at rest + TLS in transit |
| SECURITY-02 Access Logging | Compliant | ALB access logs habilitados para webhook endpoint |
| SECURITY-03 App Logging | Compliant | structlog JSON, no PII, correlationId (DP-07) |
| SECURITY-04 HTTP Headers | N/A | No HTML endpoints, bot Telegram solo |
| SECURITY-05 Input Validation | Compliant | Validación en adapter + pydantic models |
| SECURITY-06 Least Privilege | Compliant | IAM task role con permisos por tabla |
| SECURITY-07 Network Config | Compliant | Private subnet, VPC endpoint, NAT outbound |
| SECURITY-08 App Access Control | Compliant | userId-based isolation, webhook secret validation |
| SECURITY-09 Hardening | Compliant | Generic error responses, no debug mode (DP-08) |
| SECURITY-10 Supply Chain | Compliant | Pinned dependencies, no latest tags |
| SECURITY-11 Secure Design | Compliant | Rate limiter (DP-04), separation of concerns (DP-02), best-effort isolation (DP-05) |
| SECURITY-12 Auth & Credentials | N/A | No user passwords/sessions, Telegram-only |
| SECURITY-13 Integrity | Compliant | Auditable via CaptureEvent, no unsafe deserialization |
| SECURITY-14 Alerting & Monitoring | Compliant | CloudWatch 90-day retention, structured logs |
| SECURITY-15 Exception Handling | Compliant | Global error handler (DP-08), per-step try/except, fail closed |
