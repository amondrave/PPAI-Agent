# Business Rules — UOW-04 Respond & State Transition

## State Transition Rules

### BR-RSP-01: Done Transition (with confirmation)
- When user presses `[Done]`, system asks "Confirmas que completaste esta tarea? [Si] [No]".
- On `[Si]`: task transitions `PRIORITIZED|NUDGED` -> `DONE`, sets `updated_at = now`.
- On `[No]`: no state change, re-shows current Top 3.
- `DONE` is a terminal state — task is no longer eligible for Top 3 or nudges.

### BR-RSP-02: Snooze Transition (with cooldown)
- When user presses `[Snooze]`: task transitions `PRIORITIZED|NUDGED` -> `SNOOZED`.
- `snooze_count` increments by 1.
- Snooze cooldown: 1 hour. After cooldown, task auto-returns to `PENDING` (eligible for next Top 3).
- The cooldown is implemented by setting `snoozed_until = now + 1h` on the task. `list_pending` must exclude tasks where `snoozed_until > now`.
- Cache is invalidated on snooze.

### BR-RSP-03: Snooze Limit
- Maximum 3 snoozes per task (`MAX_SNOOZE_COUNT = 3`).
- On 4th snooze attempt: system blocks snooze, sends message "Ya pospusiste esta tarea 3 veces. Necesitas aclararla o completarla." and auto-triggers clarify flow.
- Snooze count resets to 0 when task returns to `PENDING` after clarification.

### BR-RSP-04: Clarify Transition
- When user presses `[Clarify]`: task transitions `PRIORITIZED|NUDGED` -> `NEEDS_CLARIFICATION` (already implemented in DecisionService.clarify).
- System sends clarification question.
- When user replies with free text: `normalized_text` is updated with the response, task transitions `NEEDS_CLARIFICATION` -> `PENDING`, `snooze_count` resets to 0.
- Cache is invalidated.

### BR-RSP-05: Clarify Response Detection
- Any text message from a user who has a task in `NEEDS_CLARIFICATION` is treated as a clarification response.
- The response updates the task's `normalized_text` (appends " | Aclarado: {response}").
- If user has multiple tasks in `NEEDS_CLARIFICATION`, the most recently clarified one (by `updated_at` DESC) receives the response.

## Idempotency Rules

### BR-RSP-06: Duplicate Callback Guard
- If a callback arrives for a task already in `DONE` state: respond "Esta tarea ya fue completada." No state change.
- If a callback arrives for a task already in `SNOOZED` state: respond "Esta tarea ya fue pospuesta." No state change.
- If a callback arrives for a task in `NEEDS_CLARIFICATION`: respond "Esta tarea espera aclaracion." No state change.
- Idempotency is checked by reading current task status before applying transition.

## Authorization Rules

### BR-RSP-07: Callback Authorization
- Before any state transition, validate `callback.from_user.id == task.user_id`.
- If mismatch: log warning `callback.unauthorized`, respond "No tienes permiso para esta accion." No state change.

## Event Recording Rules

### BR-RSP-08: Interaction Events (US-08)
- Every successful state transition records an `InteractionEvent` in `ppai-events` table.
- Event types: `TASK_DONE`, `TASK_SNOOZED`, `TASK_CLARIFIED`, `TASK_CLARIFY_RESOLVED`.
- Each event contains: `event_id`, `user_id`, `task_id`, `event_type`, `timestamp`, `correlation_id` (cycle_id), `metadata`.
- Additionally, a cycle event is recorded in `ppai-cycles` for daily aggregation.

### BR-RSP-09: Event on Error
- If event recording fails, log error but do NOT rollback the state transition (best-effort, same pattern as UOW-02/03).
- The state transition is the primary operation; event recording is secondary.

## Valid Source States for Transitions

| Action | Valid source states | Target state |
|--------|-------------------|--------------|
| done (confirmed) | PRIORITIZED, NUDGED | DONE |
| snooze | PRIORITIZED, NUDGED | SNOOZED |
| clarify | PRIORITIZED, NUDGED | NEEDS_CLARIFICATION |
| clarify_resolve | NEEDS_CLARIFICATION | PENDING |

Any transition attempt from an invalid source state is rejected with an appropriate message (BR-RSP-06).
