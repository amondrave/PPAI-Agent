# Component Dependency — PPAI v1

## Dependency Matrix

| From | To | Type | Reason |
|---|---|---|---|
| Telegram Adapter (C1) | Intake Service (S1) | Runtime | Entrada de mensajes/comandos |
| Intake Service (S1) | Capture & Normalization (C2) | Runtime | Procesar texto libre |
| Intake Service (S1) | Response Handler (C6) | Runtime | Procesar `done/snooze/clarify` |
| Capture & Normalization (C2) | Loop State Store (C8) | Runtime | Persistencia de intención normalizada |
| Capture & Normalization (C2) | Event Log (C9) | Runtime | Registro de captura |
| Decision Service (S2) | Deterministic Engine (C3) | Runtime | Cálculo Top 3 |
| Deterministic Engine (C3) | Rules Module (C4) | Runtime | Carga de reglas activas |
| Deterministic Engine (C3) | Loop State Store (C8) | Runtime | Lectura de estado/tareas |
| Nudge Orchestrator (C5) | Queue Worker (C12) | Async | Programación/ejecución de jobs |
| Queue Worker (C12) | Telegram Adapter (C1) | Runtime | Envío de nudges/reportes |
| Reporting & Rescue (C7) | Loop State Store (C8) | Runtime | Datos para reporte y rescue |
| Reporting & Rescue (C7) | Event Log (C9) | Runtime | Registro de activaciones |
| Rules Module (C4) | Admin & Access Control (C10) | Runtime | Autorización admin |
| Intake Service (S1) | Admin & Access Control (C10) | Runtime | Validación de rol por comando |
| All services | Observability (C11) | Runtime | Logs y métricas |

## Communication Patterns
- **Sync commands**: Entrada Telegram, captura, respuesta de acción, validación de permisos.
- **Async jobs**: Nudges, daily reports, rescue checks.
- **Data access**:
  - C8 como fuente operacional de estado.
  - C9 para trazabilidad y métricas.

## Logical Data Flow
1. Usuario envía mensaje por Telegram.
2. C1 enruta a C2/C6 según tipo de comando.
3. C2 guarda estado inicial en C8 y evento en C9.
4. C3 calcula Top 3 leyendo C8 + C4.
5. C5 agenda nudge en cola.
6. C12 consume job y envía por C1.
7. Usuario responde (`done/snooze/clarify`) -> C6 actualiza C8 y registra evento en C9.
8. C7 ejecuta reporte/rescue con datos de C8/C9.

## Critical Dependency Constraints
- C10 (authz) es dependencia obligatoria para acciones admin y mutaciones sensibles.
- C11 (observabilidad) debe estar presente en todos los entrypoints.
- C8 debe soportar idempotencia en transiciones para evitar corrupción por duplicados.

## Security and Reliability Impacted Dependencies
- **SECURITY-08 / SECURITY-11**: C10 aplicado antes de operaciones admin.
- **SECURITY-03 / SECURITY-14**: C11 centraliza logging/métricas.
- **NFR-02**: C12 usa reintentos controlados para jobs asíncronos.
