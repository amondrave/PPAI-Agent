# NFR Requirements — UOW-01 Capture Foundation

## NFR-CAP-01: Scalability

### Target Scale
- **Users**: 1-5 concurrent users (personal use MVP)
- **Message volume**: Low — estimado < 100 mensajes/día en total
- **Growth path**: Diseño debe permitir escalar sin reescritura, pero no se optimiza para escala en MVP

### Scalability Decisions
- DynamoDB como store principal provee escalabilidad inherente (on-demand capacity)
- ECS/Fargate permite escalar contenedores si la demanda crece
- Para MVP: single task container es suficiente, sin auto-scaling rules

---

## NFR-CAP-02: Performance

### Response Time
- **Target**: Confirmación de captura en **1-3 segundos** (desde mensaje del usuario hasta respuesta "Capturado")
- **Breakdown estimado**:
  - Telegram webhook delivery: ~100-300ms
  - Input validation + normalization: ~10-50ms
  - DynamoDB write (TaskState): ~50-200ms
  - DynamoDB read (dedup check): ~50-200ms
  - DynamoDB write (DedupRecord): ~50-200ms
  - DynamoDB write (CaptureEvent): ~50-200ms (best effort, no bloquea)
  - Telegram send confirmation: ~100-500ms
- **Budget total**: ~500-1500ms — dentro del target de 1-3s

### Performance Constraints
- Operaciones DynamoDB deben usar single-item operations (no scans) para mantener latencia predecible
- CaptureEvent write es best-effort y no debe bloquear la respuesta al usuario
- Dedup check es un GetItem por clave (userId + exactText hash), O(1)

---

## NFR-CAP-03: Availability

### Uptime Target
- **Level**: Razonable — servicio debería estar arriba la mayor parte del tiempo
- **Recovery**: Restart automático si el proceso falla (ECS task restart policy)
- **No SLA formal** para MVP, pero objetivo operacional ~99% uptime mensual

### Availability Mechanisms
- ECS Fargate task con `desiredCount=1` y restart on failure
- Health check endpoint para que ECS detecte procesos muertos
- DynamoDB es managed y no requiere gestión de disponibilidad
- Si Telegram webhook falla, los mensajes se pierden (aceptable para MVP personal)
- No se requiere queue intermedia para buffering de mensajes en MVP

---

## NFR-CAP-04: Security

### Authentication & Authorization
- **Bot-level**: Solo Telegram bot token para autenticación con Telegram API
- **User-level**: Sin autenticación adicional — cualquier usuario que hable con el bot puede usarlo
- **Data isolation**: Cada usuario opera sobre sus propias tareas (filtro por userId en queries)
- **Admin operations**: No aplican en UOW-01 (no hay operaciones admin en captura)

### Input Validation (SECURITY-05)
- Toda entrada del usuario se valida antes de procesamiento (BR-CAP-01)
- Longitud máxima de mensaje: límite de Telegram (4096 chars) + validación explícita
- Sanitización: no se ejecuta código del usuario, texto se almacena como string plano
- No hay queries SQL (DynamoDB usa API, no query language concatenable)

### Rate Limiting (SECURITY-11)
- **Rate limit**: Máximo 10 mensajes por usuario por minuto
- **Enforcement**: En la capa de Telegram Adapter, antes de procesamiento
- **Behavior al exceder**: Responder con mensaje fijo "Demasiados mensajes. Espera un momento." y descartar el mensaje
- **Implementación**: Contador en memoria (dict por userId) con ventana deslizante de 60s, o registro en DynamoDB con TTL

### Logging Security (SECURITY-03)
- Logs estructurados JSON con: timestamp, correlationId, log level, message
- **No loggear**: texto completo del usuario en logs (PII potencial). Loggear solo taskId, userId (Telegram ID numérico), y metadata operacional
- Bot token nunca en logs
- Credenciales de DynamoDB nunca en logs

### Secrets Management
- Desarrollo: archivo `.env` local (excluido de git via `.gitignore`)
- Producción: variables de entorno inyectadas en ECS task definition
- Secretos requeridos para UOW-01:
  - `TELEGRAM_BOT_TOKEN`
  - `AWS_REGION`
  - `DYNAMODB_TABLE_PREFIX` (o nombres de tabla explícitos)
  - Credenciales AWS vía IAM role del task (no access keys)

### Encryption (SECURITY-01)
- **At rest**: DynamoDB encryption at rest habilitado por defecto (AWS managed keys)
- **In transit**: HTTPS para Telegram API, HTTPS para DynamoDB API (SDK default)

---

## NFR-CAP-05: Reliability

### Error Handling (SECURITY-15)
- Toda llamada externa (DynamoDB, Telegram API) tiene try/except explícito
- **Fail strategy por operación**:
  - DynamoDB write TaskState falla → retornar error al usuario, no emitir evento
  - DynamoDB write CaptureEvent falla → log warning, captura exitosa (best effort)
  - DynamoDB write DedupRecord falla → log warning, captura exitosa (peor caso: duplicado futuro pasa)
  - Telegram send confirmation falla → log error, no reintentar (usuario puede reenviar)
- Global error handler que captura excepciones no manejadas y retorna respuesta segura

### Idempotency
- Dedup window de 5 minutos cubre reenvíos involuntarios del usuario
- DynamoDB PutItem con conditionExpression puede prevenir escrituras duplicadas si es necesario

### Data Consistency
- Estado materializado (TaskState) es fuente de verdad
- CaptureEvent es complementario (best effort), no se usa para reconstruir estado

---

## NFR-CAP-06: Maintainability

### Code Structure
- Separación clara de capas: adapter (Telegram) → service (Capture & Normalization) → repository (DynamoDB)
- Lógica de negocio aislada en módulo de servicio, sin dependencia directa de Telegram o DynamoDB
- Interfaces/protocols de repositorio para facilitar testing

### Testing Strategy
- **Unit tests**: Lógica de normalización, extracción de tags/deadlines, validación de input, dedup logic
- **Integration tests**: Flujo completo con DynamoDB real (local via DynamoDB Local o moto mock)
- **E2E tests**: Flujo contra Telegram API con mock del API (ej: usando respuestas simuladas)
- **Framework**: pytest como test runner

### Configuration
- Constantes de negocio (ACTIVE_TASK_LIMIT, DEDUP_WINDOW_SECONDS) externalizadas como variables de entorno con defaults
- No hardcodear valores en el código

---

## NFR-CAP-07: Observability

### Logging
- **Format**: JSON estructurado
- **Fields obligatorios**: timestamp (ISO 8601), correlationId (UUID por request), level, message, userId (numérico), stage
- **Export**: stdout del contenedor → CloudWatch Logs (captura automática en ECS/Fargate)
- **Retention**: Mínimo 90 días en CloudWatch (SECURITY-14)

### Metrics (operacionales, no business metrics en UOW-01)
- Capturas exitosas por minuto (contador)
- Errores de captura por minuto (contador)
- Duplicados detectados por minuto (contador)
- Latencia de procesamiento p50/p95 (histograma)
- Rate limit hits por minuto (contador)

### Alerting
- Para MVP: no se configuran alertas automáticas, pero la estructura de métricas permite agregarlas después
- CloudWatch Logs Insights disponible para queries ad-hoc

---

## NFR-CAP-08: Infrastructure as Code

### Mandate
- **Toda** la infraestructura AWS debe definirse y gestionarse via **Terraform**
- No se permiten recursos creados manualmente en la consola AWS
- Cambios de infraestructura solo via `terraform plan` + `terraform apply`

### Scope para UOW-01
- VPC, subnets, NAT gateway, VPC endpoints
- DynamoDB tables y sus configuraciones (TTL, GSIs, encryption)
- ECS cluster, task definition, service, auto-restart policies
- IAM roles y policies
- CloudWatch log groups y retention policies
- Security groups y network ACLs

### Standards
- State remoto en S3 + DynamoDB lock
- Provider versions pinned en `required_providers`
- Módulos por recurso lógico para reutilización entre UOWs
- Variables para valores configurables (table names, task count, retention days)
- Outputs para valores que otros módulos o la aplicación necesitan (table ARNs, task role ARN)

---

## NFR-CAP-09: Network & Access (SECURITY-07)

### Network Configuration
- ECS Fargate task en subnet privada (si se usa VPC)
- Acceso a DynamoDB via VPC endpoint (sin tráfico por internet)
- Acceso a Telegram API via NAT gateway (outbound HTTPS)
- No se exponen puertos inbound excepto health check interno
- Webhook de Telegram puede llegar via API Gateway o ALB con HTTPS

### IAM (SECURITY-06)
- ECS task role con permisos mínimos:
  - `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem`, `dynamodb:Query` solo sobre tablas específicas de PPAI
  - `logs:CreateLogStream`, `logs:PutLogEvents` solo sobre log group de PPAI
- No wildcard resources ni wildcard actions

---

## Security Compliance Summary (Baseline Extension)

| Rule | Status | Notes |
|---|---|---|
| SECURITY-01 Encryption | Compliant | DynamoDB encryption at rest (default), TLS in transit (SDK default) |
| SECURITY-02 Access Logging | N/A | No load balancer/API gateway/CDN definidos aún para UOW-01 (se definirán en Infrastructure Design) |
| SECURITY-03 App Logging | Compliant | JSON structured logging, no PII, correlationId, exported to CloudWatch |
| SECURITY-04 HTTP Headers | N/A | No web application — bot Telegram, no HTML endpoints |
| SECURITY-05 Input Validation | Compliant | Validación en BR-CAP-01, longitud máxima, tipo de mensaje, sanitización |
| SECURITY-06 Least Privilege | Compliant | IAM task role con permisos específicos por tabla y log group |
| SECURITY-07 Network Config | Compliant | Private subnet, VPC endpoint para DynamoDB, NAT para outbound |
| SECURITY-08 App Access Control | Compliant | userId-based data isolation, no admin ops en UOW-01 |
| SECURITY-09 Hardening | Compliant | No default credentials, generic error responses, no debug mode in prod |
| SECURITY-10 Supply Chain | Compliant | Lock file (pip freeze/poetry.lock), pinned versions, no latest tags |
| SECURITY-11 Secure Design | Compliant | Rate limiting 10/min, separation of concerns, dedup as abuse mitigation |
| SECURITY-12 Auth & Credentials | N/A | No user authentication (Telegram-only bot), no passwords, no sessions |
| SECURITY-13 Integrity | Compliant | No unsafe deserialization, auditable data changes (CaptureEvent) |
| SECURITY-14 Alerting & Monitoring | Compliant | CloudWatch logs with 90-day retention, log group permissions restricted |
| SECURITY-15 Exception Handling | Compliant | Explicit try/except on all external calls, global error handler, fail closed |
