# Business Logic Model — UOW-04 Respond & State Transition

## Service: ResponseService

Orchestrates callback processing, state transitions, and event recording.
Lives in `ppai/respond/application/response_service.py`.

### Dependencies (ports)
- `TaskStateQueryRepository` — read/write tasks (reuse from UOW-02)
- `EventRepository` — append interaction events to ppai-events
- `CycleEventRepository` — record cycle-level interaction events to ppai-cycles
- `CycleRepository` — get active cycle for correlation

### Flow 1: handle_done(user_id, task_id)

```
1. Authorize: validate user_id matches task owner (BR-RSP-07)
2. Load task by (user_id, task_id)
3. Guard: if task.status == DONE → return idempotent message (BR-RSP-06)
4. Guard: if task.status not in {PRIORITIZED, NUDGED} → return invalid state message
5. Return TransitionResult(requires_confirmation=True, message=confirmation_prompt)
```

### Flow 2: confirm_done(user_id, task_id)

```
1. Load task by (user_id, task_id)
2. Guard: same as handle_done steps 2-4
3. task.transition_to_done(now)
4. task_repo.save(task)
5. Record InteractionEvent(TASK_DONE) in ppai-events (best-effort)
6. Record cycle event INTERACTION_DONE in ppai-cycles (best-effort)
7. Invalidate Top 3 cache for user
8. Return TransitionResult(success=True, new_status=DONE)
```

### Flow 3: handle_snooze(user_id, task_id)

```
1. Authorize: validate user_id matches task owner (BR-RSP-07)
2. Load task by (user_id, task_id)
3. Guard: if task.status == SNOOZED → return idempotent message (BR-RSP-06)
4. Guard: if task.status not in {PRIORITIZED, NUDGED} → return invalid state message
5. Guard: if task.is_snooze_limit_reached() → auto-trigger clarify (BR-RSP-03)
6. task.transition_to_snoozed(now, SNOOZE_COOLDOWN)
7. task_repo.save(task)
8. Record InteractionEvent(TASK_SNOOZED) in ppai-events (best-effort)
9. Record cycle event INTERACTION_SNOOZED in ppai-cycles (best-effort)
10. Invalidate Top 3 cache for user
11. Return TransitionResult(success=True, new_status=SNOOZED, message with snooze_count)
```

### Flow 4: handle_clarify(user_id, task_id)

```
1. Authorize: validate user_id matches task owner (BR-RSP-07)
2. Load task by (user_id, task_id)
3. Guard: if task.status == NEEDS_CLARIFICATION → return idempotent message (BR-RSP-06)
4. Guard: if task.status not in {PRIORITIZED, NUDGED} → return invalid state message
5. task.transition_to_needs_clarification(now)
6. task_repo.save(task)
7. Record InteractionEvent(TASK_CLARIFIED) in ppai-events (best-effort)
8. Record cycle event INTERACTION_CLARIFIED in ppai-cycles (best-effort)
9. Invalidate Top 3 cache for user
10. Return TransitionResult(success=True, new_status=NEEDS_CLARIFICATION, message=clarify_question)
```

### Flow 5: handle_clarify_response(user_id, response_text)

```
1. Find most recent task in NEEDS_CLARIFICATION for user (by updated_at DESC)
2. If none found → return "No tienes tareas pendientes de aclaracion."
3. task.resolve_clarification(response_text, now)
4. task_repo.save(task)
5. Record InteractionEvent(TASK_CLARIFY_RESOLVED) in ppai-events (best-effort)
6. Record cycle event INTERACTION_CLARIFY_RESOLVED in ppai-cycles (best-effort)
7. Invalidate Top 3 cache for user
8. Return confirmation message with updated task text
```

## Adapter: ResponseTelegramAdapter

Connects Telegram callbacks to ResponseService. Lives in `ppai/respond/infrastructure/response_telegram_adapter.py`.

### Callback Routing

| Callback data pattern | Handler |
|----------------------|---------|
| `done:{task_id}` | → `handle_done` → sends confirmation buttons `[Si] [No]` |
| `confirm_done:{task_id}` | → `confirm_done` → sends done ACK |
| `cancel_done:{task_id}` | → re-shows Top 3 |
| `snooze:{task_id}` | → `handle_snooze` → sends snooze ACK with count |
| `clarify:{task_id}` | → `handle_clarify` → sends clarification question |

### Clarify Response Detection

- Register a `MessageHandler` with a filter: user has task in `NEEDS_CLARIFICATION`.
- On text message → `handle_clarify_response(user_id, text)`.
- Must be registered with lower priority than command handlers (/top3, /start).

## Snooze Cooldown Mechanism

The cooldown is passive (no scheduler needed):
- `snoozed_until` is stored on the task.
- `list_pending` query excludes tasks where `snoozed_until > now` by filtering in application code after DynamoDB query.
- When cooldown expires, the task naturally becomes eligible for the next `get_top3()` call.
- This avoids adding a scheduler or background job for snooze recovery.

## Module Structure

```
ppai/respond/
  __init__.py
  domain/
    __init__.py
    entities.py          # InteractionEvent, TransitionResult
    value_objects.py     # ResponseAction, constants
    exceptions.py        # InvalidTransitionError, UnauthorizedCallbackError
  application/
    __init__.py
    response_service.py  # ResponseService
    ports.py             # InteractionEventRepository protocol
  infrastructure/
    __init__.py
    response_telegram_adapter.py  # Telegram callback + message handlers
```

## Integration Points

| From | To | Mechanism |
|------|----|-----------|
| Telegram callback | ResponseService | via ResponseTelegramAdapter |
| ResponseService | TaskState repo | reuse DynamoDBTaskStateRepository |
| ResponseService | Event repo | reuse DynamoDBEventRepository (ppai-events) |
| ResponseService | Cycle event repo | reuse CycleEventRepository (ppai-cycles) |
| ResponseService | DecisionService | invalidate_cache(user_id) |
| main.py | ResponseTelegramAdapter | wiring at startup |
