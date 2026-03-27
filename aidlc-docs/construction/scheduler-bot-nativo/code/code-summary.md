# Code Summary — UOW-05 Scheduler Bot Nativo

**Fecha**: 2026-03-27  
**Rama**: `feature/uow-05-scheduler-bot-nativo`
**Stories cubiertas**: US-09 (reporte diario), US-10 (rescue mode), extensión operacional de US-06 (modo zen)

## Archivos de aplicación relevantes

### Nuevos
- `ppai/push/application/zen_session_manager.py`
- `ppai/push/application/daily_summary_builder.py`
- `ppai/push/application/rescue_evaluator.py`
- `ppai/push/infrastructure/zen_telegram_adapter.py`

### Modificados
- `ppai/push/domain/entities.py`
- `ppai/push/domain/value_objects.py`
- `ppai/push/application/nudge_service.py`
- `ppai/push/application/nudge_scheduler.py`
- `ppai/push/application/ports.py`
- `ppai/push/infrastructure/dynamodb_preferences_repo.py`
- `ppai/push/infrastructure/cycle_event_repo.py`
- `ppai/push/infrastructure/config_telegram_adapter.py`
- `ppai/main.py`

## Test coverage UOW-05

### Unit
- `tests/unit/push/test_entities_uow05.py`
- `tests/unit/push/test_zen_session_manager.py`
- `tests/unit/push/test_daily_summary_builder.py`
- `tests/unit/push/test_rescue_evaluator.py`
- `tests/unit/push/test_nudge_service_uow05.py`
- `tests/unit/push/test_nudge_scheduler_uow05.py`
- `tests/unit/push/test_zen_telegram_adapter.py`
- `tests/unit/push/test_config_adapter_uow05.py`

### Integration
- `tests/integration/push/test_dynamodb_push_repos.py`

### E2E
- `tests/e2e/test_scheduler_bot_nativo_flow.py`

### Acceptance / BDD
- `tests/features/e5/us09.feature`
- `tests/features/e5/us10.feature`
- `tests/unit/e5/test_us09.py`
- `tests/unit/e5/test_us10.py`

## Story traceability

| Story | Cobertura |
|---|---|
| US-09 | Recordatorio matutino Top 3, resumen de cierre, horarios configurables |
| US-10 | Rescue suggestion para día caído, activación manual de zen, override de silencio |
| US-06 (extensión) | Intervalo dinámico y control de sesión zen en scheduler |

## Notas de implementación

- No hubo delta de Terraform: el GSI `userId-status-index` y permisos IAM de Query ya existían.
- `NudgeService.run_tick()` pasó de un flujo solo de nudges regulares a un router con tres evaluaciones: inicio del día, cierre del día y zen.
- `ZenSessionManager` mantiene el estado efímero de sesiones zen, mientras `UserNudgePreferences` conserva la intención persistida del usuario.
- `DailySummaryBuilder` y `RescueEvaluator` mantienen el resumen y el rescue separados para que el tono y la heurística sean testeables de forma aislada.
