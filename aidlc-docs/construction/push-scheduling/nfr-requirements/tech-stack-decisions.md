# Tech Stack Decisions — UOW-03 Push & Scheduling

> Stack base heredado de UOW-01/UOW-02. Aqui se documenta solo el delta tecnico de UOW-03.

---

## Herencia sin cambios

| Componente | Decisión | Justificación |
|---|---|---|
| Lenguaje | Python 3.12.4 | Ya estandarizado |
| Runtime bot | python-telegram-bot 21.x | Ya integrado |
| DB principal | DynamoDB | Ya usada para `tasks`, `events`, `dedup`, `cycles` |
| IaC | Terraform | Mandato del proyecto |
| Container | Docker + ECS Fargate | Ya operativo en prod |
| Logging | structlog JSON | Ya integrado |
| Tests | pytest + moto | Ya operativos |

---

## Delta UOW-03

### Scheduler Strategy (Q1 = A, Q2 = C)

| Decisión | Valor |
|---|---|
| Implementación | Scheduler in-process |
| Ubicación | Mismo contenedor del bot |
| Tick | Cada 15 minutos |

**Justificación**
- Minimiza complejidad y costo.
- Evita introducir EventBridge, workers separados o colas.
- Suficiente para una sola ventana default diaria y volumen MVP.

**Tradeoff**
- Si el contenedor cae, se pierden ticks y posibles ventanas.

---

### Nueva tabla DynamoDB: `ppai-preferences` (Q3 = A)

| Atributo | Tipo | Rol |
|---|---|---|
| PK: `userId` | String | Owner de la configuracion |
| `timezone` | String | Timezone operativa |
| `maxNudgesPerDay` | Number | Default 3 |
| `silenceStart` | String | Inicio de ventana de silencio |
| `silenceEnd` | String | Fin de ventana de silencio |
| `updatedAt` | String (ISO 8601) | Timestamp |

**Observación**
- No se requiere GSI en MVP si el acceso principal es por `userId`.

---

### Persistencia de dispatch (Q4 = A)

| Decisión | Valor |
|---|---|
| `NudgeDispatch` | No tabla dedicada en MVP |
| Persistencia | Eventos/metadata en `ExecutionCycle` + event log |
| Infra adicional | Ninguna |

**Justificación**
- Reusa la trazabilidad ya existente.
- Evita otra tabla que todavía no aporta suficiente valor diferencial.

---

### Callback Security Hardening (Q9 = B)

| Decisión | Valor |
|---|---|
| Validación de owner | Obligatoria |
| Regla | `callback.from_user.id` debe coincidir con `userId` dueño del recurso |
| Alcance | Callbacks originados por nudges |

**Justificación**
- Endurece seguridad respecto a UOW-02.
- Bajo costo de implementación con alto valor preventivo.

---

### `/config` Future Compatibility (Q10 = A)

| Decisión | Valor |
|---|---|
| Estado | Interfaz prevista, no obligatoria ahora |
| Diseño esperado | No bloquear override futuro de `maxNudgesPerDay` y silencio |

**Justificación**
- Mantiene MVP enfocado.
- Evita cerrar puertas al roadmap inmediato.

---

### Observability Strategy (Q11 = A)

| Decisión | Valor |
|---|---|
| Logs por tick | No en prod |
| Logs relevantes | sent / skipped / failed |
| Nivel de detalle | Metadata minima útil para auditoría |

**Justificación**
- Reduce ruido en CloudWatch.
- Enfoca la operación en decisiones relevantes del scheduler.

---

### Lean Infra Rule (Q12 = A)

Servicios explicitamente evitados en UOW-03:

- Redis / ElastiCache
- SQS u otra cola dedicada
- Worker/container separado
- EventBridge Scheduler

**Justificación**
- Menor costo mensual
- Menor complejidad operacional
- Menor superficie de fallos para MVP

---

## Testing / Verification Delta

### Nuevas áreas a cubrir

| Tipo | Casos |
|---|---|
| Unit | Evaluación de ventana, límite diario, ventana de silencio, actividad reciente |
| Unit | Construcción del nudge, tono, selección de tarea #1 |
| Unit | Retry básico e idempotencia dentro del proceso |
| Integration | Repositorio de preferencias en DynamoDB |
| Integration | Persistencia de eventos de dispatch sobre `cycles/events` |
| E2E | Flujo scheduler -> nudge enviado / omitido / fallido |

---

## Infra Delta Esperado

| Área | Cambio esperado |
|---|---|
| DynamoDB | Nueva tabla `ppai-preferences` |
| IAM | Permisos CRUD mínimos para `ppai-preferences` |
| ECS | Sin cambio de topología |
| CloudWatch | Nuevos eventos de log de scheduler/dispatch |
| Networking | Sin cambios |

---

## Resumen de Stack para UOW-03

| Categoría | Decisión final |
|---|---|
| Scheduler | In-process, tick 15 min |
| Preferences store | DynamoDB `ppai-preferences` |
| Dispatch persistence | `ExecutionCycle` + event log |
| Callback security | Validación de owner obligatoria |
| Infra extra | Ninguna pesada |
