# Decisiones de Tech Stack — UOW-04 Respond & State Transition

## Resumen

No hay decisiones nuevas de tech stack. UOW-04 reutiliza toda la infraestructura existente.

---

## Herencia confirmada

| Componente | Tecnologia | Origen | Cambio UOW-04 |
|-----------|-----------|--------|----------------|
| Runtime | Python 3.12 + python-telegram-bot | UOW-01 | Sin cambios |
| Persistencia | DynamoDB on-demand | UOW-01 | Reutiliza ppai-tasks, ppai-events, ppai-cycles |
| Infra | ECS Fargate 256/512 | UOW-01 | Sin cambios |
| CI/CD | GitHub Actions + OIDC | UOW-01 | Sin cambios |
| Logging | structlog | UOW-01 | Sin cambios |
| Testing | pytest + moto | UOW-01 | Sin cambios |
| Cache | In-memory dict con TTL | UOW-02 | Reutiliza invalidacion existente |

## Unica configuracion nueva

### TTL en ppai-events
- Habilitar DynamoDB TTL en la tabla `ppai-events` con atributo `ttl`.
- El atributo `ttl` sera un epoch timestamp (Unix seconds) = `timestamp + 90 dias`.
- Requiere: `aws dynamodb update-time-to-live` o declaracion en Terraform.
- **Impacto**: Solo CaptureEvents existentes no tendran `ttl` (se quedan indefinidamente). Nuevos InteractionEvents si.
- **Alternativa**: Backfill de TTL en items existentes con script. No prioritario para MVP.
