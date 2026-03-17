# Unit of Work — PPAI v1

## Decomposition Strategy
- **Approach**: Journey stages
- **Target count**: 5-6 unidades (definidas: 6)
- **Execution strategy**: Híbrida (base secuencial + frentes paralelos)
- **Security/Observability handling**: Integradas dentro de cada unidad funcional
- **Prioritization rule**: Valor usuario primero
- **Infrastructure strategy**: Just-in-time por unidad

## Unit Definitions

### UOW-01 Capture Foundation
- **Goal**: Habilitar captura robusta de intención por Telegram.
- **Scope**:
  - Telegram adapter inbound
  - Capture + normalization
  - Persistencia inicial en estado materializado
  - Evento mínimo de captura
- **Primary stories**: US-01, US-02
- **Outputs**:
  - Contratos de captura
  - Flujo de validación/deduplicación
  - Base de trazabilidad de captura

### UOW-02 Decision Core
- **Goal**: Entregar Top 3 determinístico y explicable.
- **Scope**:
  - Motor de priorización determinístico
  - Reglas activas/versionadas
  - Endpoint/comando de consulta de prioridad
- **Primary stories**: US-03, US-04
- **Outputs**:
  - Ranking determinístico
  - Explicación de decisión
  - Control admin de reglas con autorización

### UOW-03 Push & Scheduling
- **Goal**: Programar y despachar nudges accionables.
- **Scope**:
  - Nudge orchestrator
  - Queue + worker de jobs
  - Retry policies y control de frecuencia
- **Primary stories**: US-05, US-06
- **Outputs**:
  - Envío de nudges por Telegram
  - Configuración de frecuencia/ventana
  - Telemetría básica de despacho

### UOW-04 Respond & State Transition
- **Goal**: Procesar acciones de usuario y cerrar ciclo de estado.
- **Scope**:
  - Handlers `done/snooze/clarify`
  - Transiciones idempotentes
  - Evento mínimo de interacción
- **Primary stories**: US-07, US-08
- **Outputs**:
  - Máquina de transición de estado operativa
  - Correlación estado-evento
  - Resiliencia ante duplicados

### UOW-05 Learn, Report & Rescue
- **Goal**: Cerrar el loop diario con reporte útil y rescue mode.
- **Scope**:
  - Generación de reporte diario
  - Detección de día caído
  - Activación de rescue mode
  - Señales conductuales básicas
- **Primary stories**: US-09, US-10, US-11, US-12
- **Outputs**:
  - Reporte no acusatorio
  - Rescue mode con propuesta accionable
  - Métricas loop base operativas

### UOW-06 Cross-Cutting Hardening In-Flow
- **Goal**: Integrar seguridad/observabilidad en cada unidad sin unidad separada.
- **Scope**:
  - AuthZ en operaciones admin y mutaciones críticas
  - Logging estructurado y no sensible
  - Métricas base y control de errores por unidad
- **Primary stories**: Transversal a US-01..US-12
- **Outputs**:
  - Checklist de hardening por UOW
  - Evidencia de cumplimiento mínimo por fase de construcción

## Implementation Notes
- UOW-06 no se ejecuta al final; se aplica como criterio de done en UOW-01..UOW-05.
- Con enfoque valor-primero, se prioriza habilitar `capture -> decide -> push` temprano.
- Infraestructura se materializa just-in-time al avanzar cada unidad.
