# Unit of Work Story Map — PPAI v1

## Story to Unit Mapping

| Story | Unit | Priority | Notes |
|---|---|---|---|
| US-01 Capture de intención | UOW-01 | High | Primer punto de valor del loop |
| US-02 Normalización mínima | UOW-01 | High | Base para priorización confiable |
| US-03 Top 3 determinístico | UOW-02 | High | Núcleo de decisión del producto |
| US-04 Gestión segura de reglas | UOW-02 | High | Admin control + auditabilidad |
| US-05 Nudge accionable | UOW-03 | High | Empuje operativo central |
| US-06 Control de intensidad/ventana | UOW-03 | Medium | Afinación de efectividad |
| US-07 Cierre de estado por respuesta | UOW-04 | High | Cierra ciclo de ejecución real |
| US-08 Registro de eventos del loop | UOW-04 | High | Trazabilidad y análisis |
| US-09 Reporte diario no acusatorio | UOW-05 | Medium | Cierre de día y continuidad |
| US-10 Activación de Rescue Mode | UOW-05 | High | Recuperación de tracción |
| US-11 Aprendizaje conductual básico | UOW-05 | Medium | Mejora iterativa de reglas |
| US-12 Observabilidad base del loop | UOW-05 | High | Métricas para operación |

## Coverage Validation
- Total historias MVP: 12
- Historias mapeadas: 12
- Cobertura: 100%

## Sequence by Value-First Strategy
1. UOW-01 (captura operativa)
2. UOW-02 (decisión Top 3)
3. UOW-03 (nudge efectivo)
4. UOW-04 (respuesta y cierre de estado)
5. UOW-05 (reporte/rescue/learn)

## Cross-Cutting Mapping (UOW-06)
Aplicar en cada historia:
- AuthZ/seguridad en comandos sensibles
- Logging estructurado sin datos sensibles
- Métricas mínimas por transición relevante

## Future Stories
- FS-01, FS-02, FS-03 quedan fuera del mapa MVP actual.
