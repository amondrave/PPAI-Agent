# Domain Entities — UOW-04 Respond & State Transition

## Modified Entities

### TaskState (extended)
Existing entity from UOW-01. UOW-04 adds:

```
TaskState
  + snoozed_until: datetime | None    # UTC timestamp when snooze cooldown expires
  + completed_at: datetime | None     # UTC timestamp when task was marked DONE
```

**New domain methods:**

```
transition_to_done(now: datetime) -> None
  PRE: status in {PRIORITIZED, NUDGED}
  POST: status = DONE, completed_at = now, updated_at = now

transition_to_snoozed(now: datetime, cooldown: timedelta) -> None
  PRE: status in {PRIORITIZED, NUDGED}, snooze_count < MAX_SNOOZE_COUNT
  POST: status = SNOOZED, snooze_count += 1, snoozed_until = now + cooldown, updated_at = now

transition_to_needs_clarification(now: datetime) -> None
  PRE: status in {PRIORITIZED, NUDGED}
  POST: status = NEEDS_CLARIFICATION, updated_at = now

resolve_clarification(response_text: str, now: datetime) -> None
  PRE: status = NEEDS_CLARIFICATION
  POST: status = PENDING, normalized_text += " | Aclarado: {response_text}", snooze_count = 0, updated_at = now

is_snooze_limit_reached() -> bool
  RETURNS: snooze_count >= MAX_SNOOZE_COUNT
```

### ExecutionCycle (extended)
Existing entity from UOW-02. UOW-04 adds interaction event recording via cycle events (same pattern as nudge events in UOW-03).

New cycle event types:
- `INTERACTION_DONE`
- `INTERACTION_SNOOZED`
- `INTERACTION_CLARIFIED`
- `INTERACTION_CLARIFY_RESOLVED`

## New Entities

### InteractionEvent
Records every user interaction with a task for audit trail (US-08).

```
InteractionEvent
  event_id: str           # UUID
  user_id: str
  task_id: str
  event_type: str         # TASK_DONE | TASK_SNOOZED | TASK_CLARIFIED | TASK_CLARIFY_RESOLVED
  correlation_id: str     # cycle_id for daily correlation
  metadata: dict          # action-specific data (e.g., snooze_count, response_text)
  timestamp: datetime     # UTC
```

**Storage**: `ppai-events` table (same table as CaptureEvent).
- PK: `userId`
- SK: `timestamp#eventId`
- Shares table schema with CaptureEvent — discriminated by `eventType`.

## New Value Objects

### ResponseAction (enum)
```
ResponseAction
  DONE = "done"
  SNOOZE = "snooze"
  CLARIFY = "clarify"
```

### TransitionResult (dataclass)
Result returned by ResponseService after processing a callback.

```
TransitionResult
  success: bool
  task_id: str
  action: ResponseAction
  message: str              # message to send back to user
  requires_confirmation: bool  # True for done action (first press)
  previous_status: TaskStatus
  new_status: TaskStatus | None  # None if no transition occurred
```

## Constants

```
MAX_SNOOZE_COUNT = 3
SNOOZE_COOLDOWN = timedelta(hours=1)
```

## State Machine Diagram

```
                  +-- done(confirmed) --> [DONE] (terminal)
                  |
[PENDING] --top3--> [PRIORITIZED] --+-- snooze --> [SNOOZED] --cooldown(1h)--> [PENDING]
                  |                 |
                  |                 +-- clarify --> [NEEDS_CLARIFICATION] --response--> [PENDING]
                  |                 |
[PENDING] --top3--> [NUDGED] ------+-- snooze(limit) --> auto-clarify --> [NEEDS_CLARIFICATION]
```
