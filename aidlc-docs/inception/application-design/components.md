# Components — PPAI v1

## Architecture Style
- **Pattern**: Modular Monolith
- **Channel Separation**: Adapter/Port explícito para Telegram
- **Execution Topology**: Servicio principal + worker de orquestación en misma base de código
- **State Strategy**: Estado materializado first + evento mínimo best effort

## Component List

### C1. Telegram Adapter
- **Purpose**: Traducir mensajes/comandos/botones de Telegram a comandos del core.
- **Responsibilities**:
  - Parseo de updates de Telegram.
  - Enrutamiento a casos de uso.
  - Render de respuestas/nudges/reportes.
- **Interfaces**:
  - Inbound: Telegram webhook/polling update handler.
  - Outbound: `CaptureUseCase`, `RespondUseCase`, `AdminConfigUseCase`.

### C2. Capture & Normalization
- **Purpose**: Transformar intención en registros operables.
- **Responsibilities**:
  - Validación básica de entrada.
  - Normalización de texto a entidad de tarea/intención.
  - Deduplicación simple por ventana.
- **Interfaces**:
  - Inbound: `captureIntent(userId, message)`
  - Outbound: `TaskStateRepository`, `EventRepository`

### C3. Deterministic Decision Engine
- **Purpose**: Calcular Top 3 y razón de priorización.
- **Responsibilities**:
  - Aplicar reglas determinísticas de ranking.
  - Adjuntar explicación de decisión.
  - Exponer puntos de ajuste por señales conductuales.
- **Interfaces**:
  - Inbound: `computeTopActions(userId, context)`
  - Outbound: `RulesRepository`, `TaskStateRepository`

### C4. Rules Module (submodules)
- **Purpose**: Gestionar reglas versionadas de priorización/adaptación.
- **Submodules**:
  - C4.1 Prioritization Rules
  - C4.2 Adaptation Rules
- **Responsibilities**:
  - CRUD/versionado de reglas.
  - Validación de cambios.
  - Auditoría de cambios.
- **Interfaces**:
  - Inbound: `getActiveRules()`, `updateRules(adminContext, payload)`
  - Outbound: `RulesRepository`, `AuditLogger`

### C5. Nudge Orchestrator
- **Purpose**: Generar y despachar nudges accionables.
- **Responsibilities**:
  - Crear payload de nudge desde top action.
  - Programar tareas para worker.
  - Aplicar control de frecuencia.
- **Interfaces**:
  - Inbound: `scheduleNudge(userId, action)`
  - Outbound: `QueuePort`, `TelegramAdapterPort`, `EventRepository`

### C6. Response Handler
- **Purpose**: Procesar `done`, `snooze`, `clarify`.
- **Responsibilities**:
  - Transición de estado inmediata.
  - Persistencia de eventos mínimos.
  - Idempotencia básica para respuestas duplicadas.
- **Interfaces**:
  - Inbound: `handleAction(userId, taskId, action)`
  - Outbound: `TaskStateRepository`, `EventRepository`, `ClarificationService`

### C7. Reporting & Rescue
- **Purpose**: Producir reporte diario y reenganche en día caído.
- **Responsibilities**:
  - Generación de resumen diario no acusatorio.
  - Detección de condición de rescue.
  - Activación de propuesta 1 tarea clave + 1 microacción.
- **Interfaces**:
  - Inbound: `runDailyReport(userId)`, `runRescueCheck(userId)`
  - Outbound: `MetricsRepository`, `TelegramAdapterPort`, `EventRepository`

### C8. Loop State Store
- **Purpose**: Fuente operacional de estado actual por usuario/tarea.
- **Responsibilities**:
  - Lectura/escritura de estados del loop.
  - Soporte para consultas de priorización y reporte.
- **Interfaces**:
  - `TaskStateRepository`

### C9. Event Log
- **Purpose**: Registro mínimo para auditoría y observabilidad.
- **Responsibilities**:
  - Persistir eventos clave del loop.
  - Correlacionar eventos con usuario/tarea.
- **Interfaces**:
  - `EventRepository`

### C10. Admin & Access Control
- **Purpose**: Control de operaciones administrativas en mismo canal Telegram con rol.
- **Responsibilities**:
  - Autenticación de actor.
  - Autorización por rol para acciones admin.
  - Verificación de ownership/alcance por comando.
- **Interfaces**:
  - `authorize(userId, command, resource)`

### C11. Observability
- **Purpose**: Logging estructurado y métricas base.
- **Responsibilities**:
  - Logger central con correlación.
  - Emisión de métricas de loop.
  - Instrumentación de errores.
- **Interfaces**:
  - `LoggerPort`, `MetricsPort`

### C12. Queue Worker
- **Purpose**: Ejecutar tareas programadas (nudge/reporte/rescue).
- **Responsibilities**:
  - Consumir cola.
  - Ejecutar handlers de jobs.
  - Reintentos y dead-letter según política.
- **Interfaces**:
  - Inbound: `QueuePort.consume()`
  - Outbound: `NudgeOrchestrator`, `ReportingRescueService`

## Security-Critical Separation
- Módulo dedicado `Admin & Access Control` (C10).
- Reglas administrativas aisladas en C4 con auditoría.
- Logger central (C11) con política de redacción de datos sensibles.
- Validación/autorización server-side para comandos de usuario/admin antes de mutaciones.
