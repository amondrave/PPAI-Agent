# Tech Stack Decisions — UOW-05 Scheduler Bot Nativo

> Solo registra deltas respecto a UOW-01/02/03/04. El stack base no cambia.

---

## Delta: Scheduler Dinámico

| Aspecto | Decisión | Razón |
|---------|----------|-------|
| Intervalo dinámico | `NudgeScheduler` acepta intervalo variable | Zen requiere precisión < 15 min (Q1: B) |
| Floor de intervalo | 5 minutos mínimo | Protección contra sobrecarga de ticks |
| Mecanismo | Recalcular intervalo en cada ciclo | Sin dependencias externas, misma arquitectura in-process |

## Delta: GSI en ppai-tasks

| Aspecto | Decisión | Razón |
|---------|----------|-------|
| Índice | GSI `userId-status-index` | Consulta eficiente de tareas por estado para resumen de cierre (Q2: B) |
| Partition key | `userId` (String) | Agrupa tareas por usuario |
| Sort key | `status` (String) | Permite query por estado específico |
| Proyección | `INCLUDE` (title, completedAt, snoozedUntil) | Solo atributos necesarios para DailySummary |
| Infraestructura | Terraform — módulo `dynamodb` existente | Consistente con NFR-PUSH-09 |

## Delta: Sanitización de Input

| Aspecto | Decisión | Razón |
|---------|----------|-------|
| Librería | Regex + strip manual | No justifica dependencia nueva para 1 campo |
| HTML strip | `re.sub(r'<[^>]+>', '', text)` | Elimina tags HTML sin dependencia |
| URL filter | `re.search(r'https?://', text)` | Previene inyección de URLs en mensajes |
| Max length | 100 caracteres | Balance entre expresividad y seguridad |

## Sin cambios

| Componente | Status |
|------------|--------|
| Python 3.12 | Heredado |
| python-telegram-bot v20+ | Heredado |
| DynamoDB on-demand | Heredado |
| ECS Fargate | Heredado |
| Terraform | Heredado |
| GitHub Actions CI/CD | Heredado |
| Logging estructurado | Heredado |
| Retry 3x / 30s backoff | Heredado |
