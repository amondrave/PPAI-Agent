# NFR Design Patterns — UOW-02 Decision Core

> Patrones DP-01..DP-08 heredados de UOW-01 sin modificación.
> Este documento define los patrones delta nuevos de UOW-02.

---

## DP-09: Pure Scoring Engine Pattern

### Pattern
El motor de scoring es un **módulo de computación pura** — sin I/O, sin estado, sin efectos secundarios. Recibe datos y retorna un resultado.

### Design
```python
# ppai/decision/domain/scoring_engine.py
from ppai.decision.domain.scoring_rules import (
    URGENCY_SCORE_24H, URGENCY_SCORE_72H, URGENCY_SCORE_FAR, URGENCY_SCORE_NONE,
    AGE_SCORE_MAX_DAYS, SNOOZE_SCORE_MULTIPLIER, SNOOZE_SCORE_MAX,
)

class ScoringEngine:
    def score(self, task: TaskState, now: datetime) -> PriorityScore:
        urgency = self._urgency_score(task.deadline, now)
        age = self._age_score(task.updatedAt, now)
        snooze = self._snooze_score(task.snoozeCount or 0)
        explanation = self._build_explanation(urgency, age, snooze, task)
        return PriorityScore(
            taskId=task.taskId,
            urgencyScore=urgency,
            ageScore=age,
            snoozeScore=snooze,
            totalScore=urgency + age + snooze,
            explanation=explanation,
        )
```

### Benefits
- **Testabilidad total**: sin mocks, sin fixtures de DB. Tests unitarios puros.
- **Determinismo**: mismo input → mismo output siempre.
- **`now` como parámetro**: permite testear cualquier fecha sin monkey-patching.

### Versioning
Constantes en `ppai/decision/domain/scoring_rules.py` — cambio de pesos = PR documentado.

---

## DP-10: In-Memory Top 3 Cache Pattern

### Pattern
Cache de Top 3 con **TTL + invalidación explícita** implementado como dict en el `DecisionService`.

### Design
```python
# Cache entry: {user_id: CacheEntry(result=Top3Result, expires_at=datetime)}
@dataclass
class CacheEntry:
    result: Top3Result
    expires_at: datetime

class DecisionService:
    def __init__(self, ...):
        self._cache: dict[str, CacheEntry] = {}

    def _get_cached(self, user_id: str) -> Top3Result | None:
        entry = self._cache.get(user_id)
        if entry and datetime.utcnow() < entry.expires_at:
            return entry.result
        return None

    def _set_cache(self, user_id: str, result: Top3Result) -> None:
        self._cache[user_id] = CacheEntry(
            result=result,
            expires_at=datetime.utcnow() + timedelta(seconds=TOP3_CACHE_TTL_SECONDS),
        )

    def invalidate_cache(self, user_id: str) -> None:
        self._cache.pop(user_id, None)
```

### Invalidación explícita
- Al capturar una tarea nueva (UOW-01 llama `invalidate_cache` via evento o directamente)
- Al procesar cualquier callback (done/snooze/clarify) sobre una tarea del Top 3
- TTL de 60s como red de seguridad (estado fresco en el siguiente minuto)

### Scope
In-process. Se pierde al reiniciar el contenedor — comportamiento aceptable (recalcula en frío).

---

## DP-11: Inline Keyboard Callback Pattern

### Pattern
Los botones inline de Telegram usan `callback_data` con formato estructurado para identificar la acción y la tarea de forma inequívoca.

### Design
```python
# Formato callback_data: "{action}:{task_id}"
# Ejemplos:
#   "done:abc-123-uuid"
#   "snooze:abc-123-uuid"
#   "clarify:abc-123-uuid"

def build_keyboard(task: TaskState) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✓ Hecho",    callback_data=f"done:{task.taskId}"),
        InlineKeyboardButton("⏸ Posponer", callback_data=f"snooze:{task.taskId}"),
        InlineKeyboardButton("? Aclarar",  callback_data=f"clarify:{task.taskId}"),
    ]])
```

### Callback Handler (routing)
```python
application.add_handler(
    CallbackQueryHandler(adapter.callback_handler, pattern=r"^(done|snooze|clarify):.+$")
)
```

### Security
- `taskId` es UUID — no guessable.
- No se incluye userId en callback_data (no necesario; se extrae de `callback.from_user.id`).
- Sin validación userId==tarea.userId en MVP (TD-DEC-01 — deuda técnica registrada).

---

## DP-12: Command Handler Pattern (/top3)

### Pattern
El comando `/top3` es el punto de entrada explícito para solicitar el Top 3.
Se registra como `CommandHandler` en python-telegram-bot.

### Design
```python
application.add_handler(CommandHandler("top3", adapter.top3_handler))
```

### Flow
```
/top3 recibido
    → DecisionService.get_top3(user_id)
        → cache hit? → retornar Top3Result del cache
        → cache miss? → query DynamoDB (GSI userId-createdAt-index)
                      → score tasks
                      → sort + select top 3
                      → update cycle + set cache
    → Telegram: enviar mensaje por cada tarea con InlineKeyboard
```

### Empty / Partial handling (BR-DEC-07)
- 0 tareas: 1 mensaje de bandeja vacía
- 1-2 tareas: mensajes de las disponibles + 1 mensaje motivacional al final

---

## DP-13: ExecutionCycle Fallback Creation

### Pattern
UOW-02 puede operar sin UOW-03 (scheduler). Si no existe ciclo activo para hoy, lo crea en modo fallback.

### Design
```python
def _get_or_create_cycle(self, user_id: str, today: date) -> ExecutionCycle:
    cycle = self.cycle_repo.get_active(user_id, today)
    if cycle is None:
        cycle = ExecutionCycle(
            cycleId=generate_id(),
            userId=user_id,
            date=today.isoformat(),
            status=CycleStatus.ACTIVE,
            top3TaskIds=[],
            manualReorders=0,
            createdAt=datetime.utcnow(),
        )
        self.cycle_repo.save(cycle)
        logger.info("cycle.created_fallback", user_id=user_id, cycle_id=cycle.cycleId)
    return cycle
```

### Invariante
Máximo 1 ciclo `active` por usuario por día. El repo usa `ConditionExpression` al crear para prevenir duplicados en race conditions.

---

## Security Compliance Summary (Baseline Extension — UOW-02)

| Rule | Status | Notas |
|---|---|---|
| SECURITY-01 Encryption | Compliant (heredado) | Sin cambios |
| SECURITY-03 App Logging | Compliant | Nuevos eventos loggeados sin PII (DP-07 heredado + nuevos eventos DEC) |
| SECURITY-05 Input Validation | Compliant | callback_data validado por regex pattern en handler registration |
| SECURITY-06 Least Privilege | Compliant | IAM role extendido con permisos Query sobre GSI y PutItem en ppai-cycles |
| SECURITY-08 App Access Control | Partial (TD-DEC-01) | Sin validación userId en callbacks — aceptado para MVP personal |
| SECURITY-11 Secure Design | Compliant | Cache sin datos sensibles, scoring puro sin I/O, callback_data con UUID |
| SECURITY-15 Exception Handling | Compliant (heredado) | Global error handler + try/except por operación |
