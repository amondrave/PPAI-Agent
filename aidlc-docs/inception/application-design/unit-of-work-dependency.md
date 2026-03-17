# Unit of Work Dependency — PPAI v1

## Execution Approach
- **Model**: Híbrido
- **Critical path**: UOW-01 -> UOW-02 -> UOW-03 -> UOW-04 -> UOW-05
- **Cross-cutting constraint**: UOW-06 aplicado sobre cada unidad funcional

## Dependency Matrix

| Unit | Depends On | Dependency Type | Reason |
|---|---|---|---|
| UOW-01 Capture Foundation | None | Start | Base del sistema y datos de entrada |
| UOW-02 Decision Core | UOW-01 | Hard | Necesita tareas normalizadas/estado |
| UOW-03 Push & Scheduling | UOW-02 | Hard | Requiere acciones priorizadas |
| UOW-04 Respond & State Transition | UOW-03 | Soft/Hard | Hard para flujo completo de nudge->respuesta; Soft para implementar handlers base |
| UOW-05 Learn, Report & Rescue | UOW-04 | Hard | Requiere eventos y estados consolidados |
| UOW-06 Cross-Cutting Hardening In-Flow | UOW-01..UOW-05 | Policy | Se integra en cada unidad |

## Parallelization Opportunities
- Tras completar UOW-01:
  - Parte de UOW-04 (handlers base + idempotencia) puede iniciar en paralelo con UOW-02.
- Durante UOW-03:
  - Observabilidad específica de dispatch puede avanzar en paralelo.
- Durante UOW-05:
  - Ajustes de reglas conductuales (US-11) puede paralelizarse parcialmente con reporte diario (US-09).

## Integration Checkpoints
1. **Checkpoint A (post UOW-02)**
   - Validar top 3 determinístico sobre datos reales de captura.
2. **Checkpoint B (post UOW-03 + base UOW-04)**
   - Validar ciclo nudge -> acción con transición de estado.
3. **Checkpoint C (post UOW-05)**
   - Validar loop completo diario + rescue + métricas.

## Rollback Considerations
- UOW-02: conservar última versión estable de reglas.
- UOW-03: fallback de envío y reintento controlado.
- UOW-04: idempotencia para evitar corrupción de estado.
- UOW-05: si falla reporte/rescue, no bloquear flujo transaccional de tareas.
