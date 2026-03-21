# Logical Components — UOW-02 Decision Core

> Componentes lógicos nuevos de UOW-02. Se añaden al bounded context `decision/`
> dentro de la estructura DDD definida en DP-02 (UOW-01).

---

## Estructura de paquete nueva

```
ppai/
  decision/                          # Bounded Context: Decision (UOW-02)
    domain/
      entities.py                    # ExecutionCycle, PriorityScore (VO), Top3Result (VO)
      value_objects.py               # CycleStatus enum
      exceptions.py                  # DecisionError hierarchy
      scoring_engine.py              # ScoringEngine — lógica pura de scoring
      scoring_rules.py               # Constantes versionadas v1.0
    application/
      decision_service.py            # DecisionService — orquesta get_top3, reorder, clarify
      ports.py                       # Protocols: TaskQueryRepo, CycleRepo
    infrastructure/
      dynamodb_task_query_repo.py    # Query tareas pending por userId (GSI)
      dynamodb_cycle_repo.py         # CRUD de ExecutionCycle
      decision_telegram_adapter.py   # /top3 handler + callback handler
    __init__.py
tests/
  features/
    e2/                              # Escenarios BDD para E2 (generados con /story-to-bdd)
      s2-1.feature
      s2-2.feature
      s2-3.feature
  unit/
    e2/
      __init__.py
      test_s2_1.py                   # Scoring + Top3 presentation (RED → GREEN)
      test_s2_2.py                   # Ambiguous task clarification
      test_s2_3.py                   # Manual reorder
    decision/
      test_scoring_engine.py         # Unit tests del scoring puro
      test_decision_service.py       # Unit tests del servicio
  integration/
    decision/
      test_dynamodb_decision_repos.py # Integration tests con moto
  e2e/
    test_top3_flow.py                # E2E flujo /top3 → DynamoDB → Telegram
```

---

## Componente: ScoringEngine

| Atributo | Valor |
|---|---|
| Ubicación | `ppai/decision/domain/scoring_engine.py` |
| Tipo | Clase de dominio — computación pura |
| Dependencias | Solo `scoring_rules.py` y entidades de dominio |
| Responsabilidad | Calcular `PriorityScore` para una `TaskState` dada |
| Estado | Sin estado (stateless) — instancia reutilizable |

**Métodos públicos:**
- `score(task: TaskState, now: datetime) -> PriorityScore`
- `rank(tasks: list[TaskState], now: datetime) -> list[PriorityScore]` — ordena por score desc + tie-breaking

---

## Componente: DecisionService

| Atributo | Valor |
|---|---|
| Ubicación | `ppai/decision/application/decision_service.py` |
| Tipo | Application Service |
| Dependencias | `TaskQueryRepository` (port), `CycleRepository` (port), `ScoringEngine` |
| Estado | Cache in-memory (`_cache: dict[str, CacheEntry]`) |

**Métodos públicos:**
- `get_top3(user_id: str) -> Top3Result`
- `reorder(user_id: str, task_id: str) -> Top3Result`
- `initiate_clarification(user_id: str, task_id: str) -> None`
- `invalidate_cache(user_id: str) -> None`

---

## Componente: TaskQueryRepository (Port)

| Atributo | Valor |
|---|---|
| Ubicación | `ppai/decision/application/ports.py` |
| Tipo | Protocol (interfaz) |
| Propósito | Abstrae las queries de tareas por userId — separado de `TaskStateRepository` (UOW-01) |

**Métodos:**
- `get_pending(user_id: str) -> list[TaskState]` — todas las tareas con status=pending

> **Nota**: `TaskStateRepository` de UOW-01 maneja escrituras y lookups por ID.
> `TaskQueryRepository` es un puerto de lectura optimizado para queries por usuario.
> Ambos pueden implementarse contra la misma tabla DynamoDB con distinto access pattern.

---

## Componente: CycleRepository (Port)

| Atributo | Valor |
|---|---|
| Ubicación | `ppai/decision/application/ports.py` |
| Tipo | Protocol (interfaz) |

**Métodos:**
- `get_active(user_id: str, date: date) -> ExecutionCycle | None`
- `save(cycle: ExecutionCycle) -> None`
- `update_top3(cycle_id: str, task_ids: list[str]) -> None`
- `increment_reorders(cycle_id: str) -> None`

---

## Componente: DynamoDBTaskQueryRepository

| Atributo | Valor |
|---|---|
| Ubicación | `ppai/decision/infrastructure/dynamodb_task_query_repo.py` |
| Tabla | `ppai-tasks` |
| Access pattern | GSI `userId-createdAt-index` + `FilterExpression(status="pending")` |

**Implementación de `get_pending`:**
```python
def get_pending(self, user_id: str) -> list[TaskState]:
    response = self.table.query(
        IndexName="userId-createdAt-index",
        KeyConditionExpression=Key("userId").eq(user_id),
        FilterExpression=Attr("status").eq("pending"),
    )
    return [self._deserialize(item) for item in response["Items"]]
```

---

## Componente: DynamoDBCycleRepository

| Atributo | Valor |
|---|---|
| Ubicación | `ppai/decision/infrastructure/dynamodb_cycle_repo.py` |
| Tabla | `ppai-cycles` (nueva) |
| Access pattern principal | GSI `userId-date-index` para `get_active` |

---

## Componente: DecisionTelegramAdapter

| Atributo | Valor |
|---|---|
| Ubicación | `ppai/decision/infrastructure/decision_telegram_adapter.py` |
| Tipo | Inbound adapter |
| Responsabilidad | Manejar `/top3` command y callbacks inline (done/snooze/clarify) |

**Handlers:**
- `top3_handler(update, context)` — responde al comando `/top3`
- `callback_handler(update, context)` — responde a callbacks de botones inline

**Registro en main.py:**
```python
application.add_handler(CommandHandler("top3", decision_adapter.top3_handler))
application.add_handler(
    CallbackQueryHandler(decision_adapter.callback_handler, pattern=r"^(done|snooze|clarify):.+$")
)
```

---

## Componente: scoring_rules.py

| Atributo | Valor |
|---|---|
| Ubicación | `ppai/decision/domain/scoring_rules.py` |
| Tipo | Módulo de constantes — sin clases ni funciones |
| Versión | v1.0 (2026-03-18) |

```python
# Urgency scores
URGENCY_SCORE_24H  = 10
URGENCY_SCORE_72H  = 7
URGENCY_SCORE_FAR  = 4
URGENCY_SCORE_NONE = 3

# Age score
AGE_SCORE_MAX_DAYS = 7       # 1 punto/día, techo 7

# Snooze score
SNOOZE_SCORE_MULTIPLIER = 2  # snoozeCount * 2
SNOOZE_SCORE_MAX        = 10 # techo

# Cache
TOP3_CACHE_TTL_SECONDS = 60
```

---

## Wiring en main.py (delta)

```python
# Nuevas dependencias a instanciar en build_app()
task_query_table  = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "tasks"))
cycle_table       = dynamodb.Table(table_name(settings.dynamodb_table_prefix, "cycles"))

task_query_repo   = DynamoDBTaskQueryRepository(task_query_table)
cycle_repo        = DynamoDBCycleRepository(cycle_table)
scoring_engine    = ScoringEngine()

decision_service  = DecisionService(
    task_query_repo=task_query_repo,
    cycle_repo=cycle_repo,
    scoring_engine=scoring_engine,
)

decision_adapter  = DecisionTelegramAdapter(decision_service)

# Handlers adicionales
application.add_handler(CommandHandler("top3", decision_adapter.top3_handler))
application.add_handler(
    CallbackQueryHandler(decision_adapter.callback_handler, pattern=r"^(done|snooze|clarify):.+$")
)
```
