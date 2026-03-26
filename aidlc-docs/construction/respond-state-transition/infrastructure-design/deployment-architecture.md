# Deployment Architecture — UOW-04 Respond & State Transition

> UOW-04 no introduce componentes de despliegue nuevos. La arquitectura de deployment
> es idéntica a UOW-03. Este documento documenta el flujo de datos específico de UOW-04
> dentro de la infraestructura existente.

---

## Topología de deployment (sin cambios)

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS Cloud (us-east-1)                    │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    VPC (ppai-vpc)                      │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │              ECS Fargate (ppai-bot)              │  │  │
│  │  │                                                 │  │  │
│  │  │  python-telegram-bot                            │  │  │
│  │  │    ├── MessageHandler (captura)         UOW-01  │  │  │
│  │  │    ├── CommandHandler /top3             UOW-02  │  │  │
│  │  │    ├── CommandHandler /config           UOW-03  │  │  │
│  │  │    ├── CallbackQueryHandler             UOW-04  │  │  │
│  │  │    │   (done/confirm_done/cancel_done           │  │  │
│  │  │    │    snooze/clarify)                         │  │  │
│  │  │    └── MessageHandler (clarify response) UOW-04 │  │  │
│  │  │                                                 │  │  │
│  │  │  NudgeScheduler (background thread)     UOW-03  │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │           │              │             │               │  │
│  │           ▼              ▼             ▼               │  │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────┐        │  │
│  │  │ppai-tasks│  │ ppai-events  │  │ppai-cycles│        │  │
│  │  │(DynamoDB)│  │(DynamoDB+TTL)│  │(DynamoDB) │        │  │
│  │  └──────────┘  └──────────────┘  └──────────┘        │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
            ▲                          │
            │ callback_query           │ reply_text
            │                          ▼
      ┌──────────────────────────────────┐
      │         Telegram Bot API         │
      └──────────────────────────────────┘
            ▲                          │
            │ tap button               │ message
            │                          ▼
      ┌──────────────────────────────────┐
      │            Usuario               │
      └──────────────────────────────────┘
```

---

## Flujos de datos UOW-04

### Flujo 1: Done (con confirmación)

```
Usuario tap [✓ Hecho]
  → Telegram callback_query: "done:{task_id}"
  → ECS: CallbackQueryHandler
    → ResponseService.handle_done(user_id, task_id)
      → ppai-tasks: GetItem (verificar estado + autorizar)
      → Telegram: edit_message_reply_markup → [Sí] [No]

Usuario tap [Sí]
  → Telegram callback_query: "confirm_done:{task_id}"
  → ECS: CallbackQueryHandler
    → ResponseService.confirm_done(user_id, task_id)
      → ppai-tasks: PutItem (status=DONE, completedAt=now)
      → ppai-events: PutItem (InteractionEvent + ttl)
      → ppai-cycles: UpdateItem (append INTERACTION_DONE)
      → DecisionService: invalidate_cache(user_id)
      → Telegram: reply "Anotado. ✓"
```

### Flujo 2: Snooze

```
Usuario tap [⏸ Posponer]
  → Telegram callback_query: "snooze:{task_id}"
  → ECS: CallbackQueryHandler
    → ResponseService.handle_snooze(user_id, task_id)
      → ppai-tasks: GetItem (verificar estado + snooze_count)
      → IF snooze_count < 3:
        → ppai-tasks: PutItem (status=SNOOZED, snooze_count++, snoozedUntil)
        → ppai-events: PutItem (InteractionEvent + ttl)
        → ppai-cycles: UpdateItem (append INTERACTION_SNOOZED)
        → Telegram: reply "Pospuesto. Te lo recuerdo más tarde."
      → ELSE (4th snooze):
        → auto-trigger clarify flow
```

### Flujo 3: Clarify + Response

```
Usuario tap [? Aclarar]
  → Telegram callback_query: "clarify:{task_id}"
  → ECS: CallbackQueryHandler
    → ResponseService.handle_clarify(user_id, task_id)
      → ppai-tasks: PutItem (status=NEEDS_CLARIFICATION)
      → ppai-events: PutItem (InteractionEvent + ttl)
      → Telegram: reply "¿Qué necesitas para avanzar?"

Usuario envía texto libre (respuesta)
  → Telegram message
  → ECS: MessageHandler (clarify response detector)
    → ResponseService.handle_clarify_response(user_id, text)
      → ppai-tasks: Query (user tasks en NEEDS_CLARIFICATION)
      → ppai-tasks: PutItem (status=PENDING, snooze_count=0, text actualizado)
      → ppai-events: PutItem (InteractionEvent + ttl)
      → ppai-cycles: UpdateItem (append INTERACTION_CLARIFY_RESOLVED)
      → Telegram: reply "Aclarado. La tarea vuelve a tu bandeja."
```

---

## Latencia estimada por flujo

| Flujo | Operaciones DynamoDB | Latencia estimada |
|---|---|---|
| Done (2 callbacks) | 2 GetItem + 1 PutItem + 2 eventos | ~800ms total |
| Snooze | 1 GetItem + 1 PutItem + 2 eventos | ~350ms |
| Clarify | 1 GetItem + 1 PutItem + 1 evento | ~250ms |
| Clarify Response | 1 Query + 1 PutItem + 2 eventos | ~400ms |

Todos dentro del target NFR-RSP-02 de < 500ms por callback individual.

---

## Rollout strategy

1. **Terraform apply**: Agregar TTL a `ppai-events` (non-destructive, backwards compatible)
2. **Docker build + push ECR**: Nuevo código con ResponseService + handlers
3. **ECS deploy**: Force new deployment (rolling update, 0 downtime)
4. **Verificación**: Probar flujos Done/Snooze/Clarify en Telegram
