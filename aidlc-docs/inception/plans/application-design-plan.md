# Application Design Plan — PPAI v1

## Objective
Definir componentes, interfaces de alto nivel, métodos principales, servicios de orquestación y dependencias para implementar el loop `capture -> decide -> push -> respond -> learn` en Telegram.

## Design Checklist
- [x] Confirm architectural style for MVP v1
- [x] Confirm module boundaries and ownership
- [x] Confirm state and event integration pattern
- [x] Confirm service orchestration and scheduling strategy
- [x] Confirm security-critical module separation
- [x] Generate `aidlc-docs/inception/application-design/components.md`
- [x] Generate `aidlc-docs/inception/application-design/component-methods.md`
- [x] Generate `aidlc-docs/inception/application-design/services.md`
- [x] Generate `aidlc-docs/inception/application-design/component-dependency.md`
- [x] Validate design consistency and completeness

## Proposed Baseline (for confirmation)
- Telegram as single channel adapter (v1)
- Deterministic decision engine (rules-first)
- Materialized state as primary operational source
- Minimal event log for audit/observability
- Orchestration services for nudges, daily report, rescue mode

## Planning Questions

## Question 1
¿Qué estilo arquitectónico prefieres para v1?

A) Monolito modular (módulos internos bien separados)
B) Servicio principal + worker(s) de orquestación (2-3 procesos)
C) Microservicios desde v1
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
¿Cómo quieres separar la capa de canal (Telegram) del core de negocio?

A) Adapter/port explícito (hexagonal-like)
B) Integración directa en capa de aplicación
C) Híbrido (adapter parcial)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
Para estado + eventos, ¿qué consistencia operativa priorizamos?

A) Update estado primero, luego evento (best effort)
B) Evento primero, luego proyección de estado
C) Transacción única estado+evento (si stack lo permite)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
¿Cómo orquestamos jobs de nudge/reporte/rescue en v1?

A) Scheduler interno del servicio principal
B) Cola + worker dedicado para tareas programadas
C) Cron externo/managed scheduler disparando handlers
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 5
¿Qué frontera de seguridad aplicamos para operaciones administrativas (reglas/config)?

A) Endpoints/comandos admin separados con autorización estricta
B) Mismo canal que usuario final con validación por rol
C) Solo configuración por archivo/env en v1
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6
¿Qué estrategia de observabilidad de aplicación quieres en diseño v1?

A) Logging estructurado + métricas básicas
B) Logging estructurado + métricas + trazas distribuidas
C) Logging básico en v1, ampliar luego
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
¿Qué nivel de desacople quieres para el motor de reglas (priorización y aprendizaje)?

A) Motor único con submódulos internos
B) Dos motores separados (priorización y adaptación)
C) Plugin-style rules registry desde v1
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Mandatory Artifacts to Generate After Approval
- [ ] `aidlc-docs/inception/application-design/components.md`
- [ ] `aidlc-docs/inception/application-design/component-methods.md`
- [ ] `aidlc-docs/inception/application-design/services.md`
- [ ] `aidlc-docs/inception/application-design/component-dependency.md`

## Approval Gate
No design artifact generation starts until all `[Answer]:` tags are completed, ambiguities are resolved, and this plan is explicitly approved.
