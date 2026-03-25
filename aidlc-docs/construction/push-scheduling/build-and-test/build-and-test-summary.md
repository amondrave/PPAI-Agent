# UOW-03 Push & Scheduling — Build and Test Summary

**Fecha**: 2026-03-25
**Rama**: `feature/uow-03-push-scheduling`
**PR**: #6 → mergeado a `main`
**Resultado**: ✅ COMPLETO

---

## Test Results

| Suite | Tests | Passing | Failing |
|-------|-------|---------|---------|
| Unit — domain | 14 | 14 | 0 |
| Unit — nudge_service | 28 | 28 | 0 |
| Unit — nudge_scheduler | 8 | 8 | 0 |
| Unit — telegram_push_adapter | 11 | 11 | 0 |
| Unit — BDD acceptance (US-05, US-06) | 11 | 11 | 0 |
| Integration — DynamoDB (LocalStack) | 14 | 14 | 0 |
| E2E — push flow | 9 | 9 | 0 |
| **UOW-03 subtotal** | **95** | **95** | **0** |
| UOW-01 (sin regresiones) | 75 | 75 | 0 |
| UOW-02 (sin regresiones) | 93 | 93 | 0 |
| **TOTAL** | **262** | **262** | **0** |

---

## LocalStack

- Tabla `ppai-preferences` creada via `scripts/create-local-tables.py`
- 14/14 integration tests pasaron contra LocalStack 3.4
- `ppai-cycles` existente — sin regresiones en eventos de nudge

---

## Prueba Manual Telegram

| Acción | Resultado |
|--------|-----------|
| Bot arranca (`python -m ppai.main`) | ✅ `nudge_scheduler.started` en logs |
| Enviar tarea por texto libre | ✅ `sendMessage 200 OK` |
| `/top3` | ✅ `cycle.created_fallback + top3.computed + sendMessage 200` |
| Nudge proactivo del scheduler | ✅ `sendMessage 200 OK` antes del comando |

**Nota**: 409 Conflict esperados — instancia ECS prod también en polling con mismo token. No es bug.

---

## CI/CD

- Branch push → GitHub Actions `test` job: ✅ verde
- PR #6 mergeado → pipeline completo activado en `main`:
  1. `test` — 262 tests
  2. `build-push` — imagen Docker → ECR
  3. `terraform apply` — crea tabla `ppai-preferences` + permisos IAM
  4. `deploy` — ECS Fargate actualizado con UOW-03

---

## Terraform Delta

| Recurso | Acción |
|---------|--------|
| `aws_dynamodb_table.preferences` | CREATE — tabla `ppai-preferences` |
| `aws_iam_role_policy.task_role` | UPDATE — permisos GetItem/PutItem sobre `ppai-preferences` |

---

## Fixes aplicados en Build and Test

| Fix | Descripción |
|-----|-------------|
| `scripts/create-local-tables.py` | Agregada tabla `ppai-preferences` para LocalStack |

---

## Business Rules verificadas

| ID | Regla | Tests |
|----|-------|-------|
| BR-PUSH-01 | Solo enviar si hay tareas en Top 3 | test_skipped_when_top3_is_empty |
| BR-PUSH-02 | Respetar ventana de silencio | test_silence_window_*, US-06 BDD |
| BR-PUSH-03 | Cap diario de nudges | test_daily_cap_*, US-06 BDD |
| BR-PUSH-04 | Re-engagement tras 24h inactividad | test_re_engagement_* |
| BR-PUSH-05 | Retry hasta 3 intentos | test_failure_after_all_retries |
| BR-PUSH-06 | Tone positivo sin frases prohibidas | test_build_nudge_message_no_prohibited_phrases |
| BR-PUSH-07 | Callback solo del dueño de la tarea | test_rejects_callback_from_different_user |
