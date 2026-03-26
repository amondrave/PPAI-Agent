# Functional Design Plan — UOW-04 Respond & State Transition

## Unit Context
- **Unit**: UOW-04 Respond & State Transition
- **Goal**: Procesar acciones de usuario (done/snooze/clarify) y cerrar ciclo de estado
- **Stories**: US-07 (Cierre de estado por respuesta), US-08 (Registro de eventos del loop)
- **Dependencies**: UOW-01 (TaskState), UOW-02 (DecisionService, callbacks), UOW-03 (NudgeService)

## Gap Analysis (what exists vs what's needed)

### Already exists:
- Callback handler parses `done:task_id`, `snooze:task_id`, `clarify:task_id`
- ACK messages sent + keyboard removed
- `clarify` transitions task to `NEEDS_CLARIFICATION`
- `TaskStatus` enum has `DONE`, `SNOOZED`, `NEEDS_CLARIFICATION`
- `snooze_count` field on TaskState
- `CaptureEvent` + `DynamoDBEventRepository` for capture events
- `CycleEventRepo.record_nudge_event()` for nudge events
- Cache invalidation on callbacks

### Missing (scope of UOW-04):
- `done` callback: no status transition to `DONE`
- `snooze` callback: no status transition to `SNOOZED`, no `snooze_count` increment
- No interaction events recorded (done/snooze/clarify)
- No idempotency guard on duplicate callbacks
- No domain methods for state transitions (only `transition_to_pending`)

## Design Steps

- [ ] Step 1: Define state transition rules (BR-RSP-01..06)
- [ ] Step 2: Define interaction event model (InteractionEvent entity)
- [ ] Step 3: Define idempotency rules for duplicate callbacks
- [ ] Step 4: Define ResponseService orchestration logic
- [ ] Step 5: Define error handling and recovery strategies
- [ ] Step 6: Generate functional design artifacts

## Clarifying Questions

### Q1: Snooze behavior
When a user snoozes a task, should it return to `PENDING` (re-eligible for next Top 3 cycle) or stay as `SNOOZED` until a cooldown period passes?

Options:
A) Immediate return to PENDING (simplest — next /top3 may pick it up again)
B) SNOOZED for a fixed cooldown (e.g., 1 hour) then auto-return to PENDING
C) SNOOZED until next day's cycle

[Answer]: B

### Q2: Done confirmation
When marking a task as `DONE`, should there be any confirmation step or is the single button press enough?

Options:
A) Single press — done immediately (current UX)
B) Ask "Are you sure?" before marking done

[Answer]: B

### Q3: Snooze limit
Should there be a maximum number of snoozes per task? The `snooze_count` field exists. After hitting the limit, what happens?

Options:
A) No limit — user can snooze indefinitely
B) Max 3 snoozes, then force clarify or escalate
C) Max 5 snoozes, then auto-archive with warning

[Answer]: B

### Q4: Event storage strategy
For interaction events (US-08), should we:

Options:
A) Extend existing `ppai-events` table with new event types (TASK_DONE, TASK_SNOOZED, TASK_CLARIFIED)
B) Add interaction events as cycle events in `ppai-cycles` (like nudge events)
C) Both — events table for audit trail + cycle for daily aggregation

[Answer]:  C

### Q5: Clarify response handling
When the user answers a clarification question, how should the system process it?

Options:
A) Simple: user text updates `normalized_text`, task returns to PENDING
B) User selects from options (a/b), system tags the task accordingly, returns to PENDING
C) Keep it minimal for MVP — clarify just marks the task, user manually resolves and does /top3 again

[Answer]: A

### Q6: Callback authorization
Should we validate that the user pressing the callback button is the same user who owns the task? (UOW-06 security requirement)

Options:
A) Yes — validate `callback.from_user.id == task.user_id` before any transition
B) No — Telegram inline buttons are already scoped to the chat

[Answer]: A
