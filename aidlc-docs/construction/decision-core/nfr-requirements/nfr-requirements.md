# NFR Requirements — UOW-02 Decision Core

> La mayoría de NFRs se heredan de UOW-01. Este documento registra solo los delta
> y confirma la herencia explícita de cada categoría.

---

## NFR-DEC-01: Scalability (heredado UOW-01)

Igual que NFR-CAP-01. MVP personal, 1-5 usuarios concurrentes.
DynamoDB on-demand capacity cubre el volumen sin configuración adicional.

**Delta UOW-02:** El nuevo GSI `userId-createdAt-index` sobre `ppai-tasks` agrega
capacidad de lectura por usuario, no afecta escrituras ni escalabilidad general.

---

## NFR-DEC-02: Performance

### Scoring (in-memory)
- Computación pura sin I/O: **< 5ms** para cualquier lista de tareas en escala MVP.
- No representa cuello de botella.

### DynamoDB Query (Q1 = B)
- **Patrón**: GSI `userId-createdAt-index` (PK=userId, SK=createdAt) + `FilterExpression(status="pending")`.
- **Latencia estimada**: 50–200ms por query (igual que UOW-01).
- **Justificación**: El volumen MVP es bajo (< 50 tareas por usuario). Un FilterExpression
  con GSI es eficiente para este rango. Se puede migrar a GSI PK=userId, SK=status
  si el volumen crece y el FilterExpression se vuelve ineficiente.

### Cache de Top 3 (Q4 = B)
- **Tipo**: In-memory dict `{userId: (Top3Result, expires_at)}`.
- **TTL**: 60 segundos por usuario.
- **Invalidación explícita**: El cache se invalida cuando el usuario captura una tarea nueva
  o cuando se procesa un callback (done/snooze/clarify) sobre una tarea del Top 3.
- **Beneficio**: Evita re-queries a DynamoDB si el usuario pide `/top3` múltiples veces
  en un minuto (comportamiento común al explorar el bot).
- **Scope**: In-process. Se pierde si el contenedor reinicia — aceptable para MVP.

### Response Time Target
- `/top3` con cache hit: **< 100ms**
- `/top3` con cache miss (query DynamoDB): **< 500ms**

---

## NFR-DEC-03: Availability (heredado UOW-01)

Igual que NFR-CAP-03. ECS Fargate desiredCount=1, restart on failure, ~99% uptime objetivo.

---

## NFR-DEC-04: Security

### Inline Keyboard Callbacks (Q3 = B — YAGNI)
- No se valida `callback.from_user.id == tarea.userId` en MVP.
- **Justificación**: Bot de uso personal exclusivo. No hay grupos ni usuarios compartidos.
- **Riesgo aceptado**: Si el bot se añade a un grupo en el futuro, cualquier miembro podría
  pulsar botones de otros. Registrado como deuda técnica para resolver antes de escalar.

### callback_data Security
- `callback_data` contiene `{action}:{taskId}` (ej: `done:abc-123`).
- `taskId` es un UUID — no guessable, bajo riesgo de enumeración.
- No se incluyen datos sensibles (texto de tarea, userId) en callback_data.

### AuthZ en Reordenamiento (US-04 — admin)
- En MVP no existe operación de gestión de reglas (reglas hardcoded, Q9=C en FD).
- No hay endpoints admin que proteger en UOW-02.

### Resto de seguridad (heredado UOW-01)
- Input validation, logging sin PII, secrets management, encryption: igual que NFR-CAP-04.

---

## NFR-DEC-05: Reliability

### snoozeCount — Campo nuevo en TaskState (Q2 = A)
- DynamoDB es schemaless: añadir `snoozeCount` con `default=0` no requiere migración.
- Tareas existentes sin el campo retornan `None` en boto3; el código trata `None` como `0`.
- **Invariante**: `snoozeCount` solo se incrementa en UOW-04 (handler de Posponer).
  UOW-02 solo lo lee.

### Cache Invalidation
- Si el cache no se invalida correctamente, el usuario podría ver un Top 3 desactualizado.
- **Mitigación**: Invalidar en cualquier mutación de TaskState (captura nueva, callback recibido).
- **Fallback**: TTL de 60s asegura que el estado sea fresco en el siguiente minuto.

### Resto de reliability (heredado UOW-01)
- Error handling, idempotency, data consistency: igual que NFR-CAP-05.

---

## NFR-DEC-06: Maintainability

### Testing Strategy (TDD/BDD — nuevo en UOW-02)
- **BDD**: Escenarios Gherkin para S2.1, S2.2, S2.3 generados con `/story-to-bdd` antes del código.
- **Unit tests**: Scoring engine (puro, sin I/O — 100% cobertura posible), cache logic.
- **Integration tests**: DecisionService con DynamoDB mock (moto), incluyendo GSI queries.
- **E2E tests**: Flujo completo `/top3` → DynamoDB → respuesta Telegram simulada.
- **Framework**: `pytest` (heredado). `behave` para correr `.feature` files en CI (nuevo).

### Scoring Rules Versioning (Q9=C del FD)
- Constantes en `ppai/decision/domain/scoring_rules.py` con comentario de versión.
- Cambio de pesos = PR + nuevo commit, trazable en git history.

### Resto de maintainability (heredado UOW-01)
- Separación de capas, interfaces/protocols de repositorio: igual que NFR-CAP-06.

---

## NFR-DEC-07: Observability (heredado UOW-01 + delta)

**Nuevos eventos a loggear en UOW-02:**
- `top3.requested` — userId, cycle_id, timestamp
- `top3.computed` — userId, task_ids, scores (sin texto de tarea), cache_hit bool
- `top3.presented` — userId, task_ids, timestamp
- `manual_reorder.received` — userId, task_id, from_pos, to_pos
- `clarification.initiated` — userId, task_id
- `cache.hit` / `cache.miss` — userId, ttl_remaining

Formato JSON heredado de UOW-01. Todos los logs a stdout → CloudWatch.

---

## NFR-DEC-08: Infrastructure as Code (heredado UOW-01)

Toda infraestructura nueva de UOW-02 vía Terraform:
- GSI `userId-createdAt-index` en módulo `dynamodb/` existente.
- Tabla nueva `ppai-cycles` para ExecutionCycle.
- No se requieren nuevos módulos de red/IAM (se reutilizan los de UOW-01).

---

## Security Compliance Summary (Baseline Extension — delta UOW-02)

| Rule | Status | Notas |
|---|---|---|
| SECURITY-01 Encryption | Compliant (heredado) | Sin cambios |
| SECURITY-05 Input Validation | Compliant | callback_data validado por formato antes de procesar |
| SECURITY-06 Least Privilege | Compliant | IAM role existente ya incluye Query/GetItem en ppai-tasks; añadir permisos para ppai-cycles |
| SECURITY-08 App Access Control | Partial (YAGNI) | Sin validación userId en callbacks — deuda técnica registrada |
| SECURITY-11 Secure Design | Compliant | Cache in-memory sin datos sensibles, TTL limita staleness |
| SECURITY-15 Exception Handling | Compliant (heredado) | try/except en todas las llamadas externas |

---

## Deuda Técnica Registrada

| ID | Descripción | Condición de resolución |
|---|---|---|
| TD-DEC-01 | Sin validación userId en inline keyboard callbacks | Antes de añadir el bot a grupos o usuarios múltiples |
| TD-DEC-02 | GSI con FilterExpression en lugar de GSI por status | Si snoozeCount/status queries superan 200ms bajo carga real |
