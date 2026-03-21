# Tech Stack Decisions — UOW-02 Decision Core

> Stack base heredado de UOW-01. Solo se documenta el delta de UOW-02.

---

## Herencia de UOW-01 (sin cambios)

| Componente | Decisión | Justificación |
|---|---|---|
| Lenguaje | Python 3.12.4 | StrEnum, pyenv configurado |
| Framework web | python-telegram-bot 21.x | Ya integrado |
| DB | DynamoDB (AWS) | Serverless, on-demand, ya en uso |
| IaC | Terraform | Mandato del proyecto |
| Container | Docker + ECS Fargate | Ya definido |
| Tests | pytest | Ya configurado con 75 tests passing |
| Logging | structlog (JSON) | Ya integrado |
| Config | pydantic-settings | Ya integrado |

---

## Delta UOW-02

### Nueva tabla DynamoDB: `ppai-cycles`

| Atributo | Tipo | Rol |
|---|---|---|
| PK: `cycleId` | String (UUID) | Identificador único |
| `userId` | String | Owner |
| `date` | String (YYYY-MM-DD) | Un ciclo por usuario por día |
| `status` | String | `active` \| `closed` |
| `top3TaskIds` | List[String] | Task IDs del Top 3 actual |
| `manualReorders` | Number | Contador de reordenamientos |
| `createdAt` | String (ISO 8601) | Timestamp |
| `closedAt` | String \| null | Timestamp de cierre |

**GSI sobre `ppai-cycles`**: `userId-date-index` (PK=userId, SK=date)
— permite buscar el ciclo activo de un usuario para una fecha dada.

### Nuevo GSI en tabla existente `ppai-tasks`

| GSI | PK | SK | Propósito |
|---|---|---|---|
| `userId-createdAt-index` | `userId` | `createdAt` | Query tareas de un usuario ordenadas por creación + FilterExpression(status) |

**Nota**: `snoozeCount` se añade como atributo nuevo a `ppai-tasks`.
DynamoDB es schemaless — no requiere migración. `None` se trata como `0` en código.

### Cache in-memory (nuevo en UOW-02)

| Decisión | Valor |
|---|---|
| Implementación | `dict` en `DecisionService` instance |
| TTL | 60 segundos |
| Invalidación | Al capturar tarea nueva o procesar callback sobre Top 3 |
| Librería | Ninguna — implementación propia simple (< 20 líneas) |

**Justificación**: No se introduce Redis ni memcached. El volumen MVP no justifica
infraestructura de cache externa. Un `dict` con timestamp de expiración es suficiente
y mantiene el sistema sin dependencias nuevas.

### BDD runner: `behave` (nuevo en UOW-02)

```
behave==1.2.6
```

Se añade a `requirements.txt`. Corre los `.feature` files generados con `/story-to-bdd`.
Se integra en el pipeline de tests junto con pytest:

```bash
# Unit + integration tests
pytest tests/unit/ tests/integration/

# BDD acceptance tests
behave tests/features/

# E2E
pytest tests/e2e/
```

### Scoring rules module (nuevo)

```
ppai/decision/domain/scoring_rules.py
```

Constantes puras sin dependencias. Permite testear el scoring en aislamiento total.

```python
# scoring_rules.py — v1.0 (2026-03-18)
URGENCY_SCORE_24H = 10
URGENCY_SCORE_72H = 7
URGENCY_SCORE_FAR = 4
URGENCY_SCORE_NONE = 3

AGE_SCORE_MAX_DAYS = 7      # 1 punto/día, techo 7
SNOOZE_SCORE_MULTIPLIER = 2 # snoozeCount * 2
SNOOZE_SCORE_MAX = 10       # techo

TOP3_CACHE_TTL_SECONDS = 60
```
