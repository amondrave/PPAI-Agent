# Services — PPAI v1

## Service Topology
- **App Service (Core API + Telegram Adapter)**
  - Maneja entrada/salida de Telegram
  - Ejecuta casos de uso sincrónicos (captura, respuesta)
  - Publica trabajos a cola (nudges/reportes/rescue)
- **Orchestration Worker Service**
  - Consume cola de jobs programados
  - Ejecuta nudge dispatch, daily report y rescue checks

## Service Definitions

### S1. Intake Service
- **Owns**: C1, C2, parte de C6
- **Responsibilities**:
  - Recepción de comandos de usuario
  - Captura/normalización
  - Comandos de acción (`done/snooze/clarify`)
- **Key Interactions**:
  - C8 (estado), C9 (eventos), C11 (observabilidad)

### S2. Decision Service
- **Owns**: C3, C4
- **Responsibilities**:
  - Cálculo Top 3
  - Exposición/uso de reglas activas
  - Ajustes administrativos controlados
- **Key Interactions**:
  - C8 (lectura estado), C9 (eventos), C10 (autorización admin)

### S3. Orchestration Service
- **Owns**: C5, C12
- **Responsibilities**:
  - Programación y ejecución de nudges/reportes/rescue
  - Políticas de reintento
  - Envío efectivo por adapter
- **Key Interactions**:
  - QueuePort, C1, C7, C11

### S4. Reporting & Learning Service
- **Owns**: C7
- **Responsibilities**:
  - Generación de reporte diario
  - Detección/activación rescue mode
  - Ajustes básicos por señales conductuales
- **Key Interactions**:
  - C8, C9, C3/C4, C11

### S5. Security & Admin Service
- **Owns**: C10
- **Responsibilities**:
  - Autenticación/autorización server-side
  - Controles de acceso para operaciones admin
  - Validación de ownership para recursos
- **Key Interactions**:
  - Todos los entrypoints que mutan estado o reglas

### S6. Observability Service
- **Owns**: C11
- **Responsibilities**:
  - Logging estructurado con correlation ID
  - Métricas de loop operativas
  - Señales de error y timing

## Orchestration Patterns
- **Synchronous path**: Telegram update -> Intake -> (Decision/State) -> response
- **Async path**: Scheduling trigger -> Queue -> Worker -> send/report/rescue
- **Admin path**: Telegram admin command -> AuthZ guard -> Rules update -> audit log

## Reliability and Consistency Decisions
- Estado materializado se actualiza primero.
- Evento mínimo se persiste después (best effort).
- Reintentos para envíos y jobs asíncronos.
- Idempotencia en transiciones de estado por correlación.

## Security Notes (Design-Level)
- Endpoints/comandos administrativos y comandos usuario comparten canal, pero con autorización por rol server-side.
- No se permite mutación de reglas sin verificación de permisos.
- Eventos/logs deben omitir secretos y datos sensibles.
