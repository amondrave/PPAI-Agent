# Component Methods — PPAI v1

## C1 Telegram Adapter
- `handleUpdate(update: TelegramUpdate): AdapterResponse`
- `sendMessage(userId: string, payload: MessagePayload): SendResult`
- `sendNudge(userId: string, nudge: NudgePayload): SendResult`

## C2 Capture & Normalization
- `captureIntent(userId: string, rawText: string, source: string): CaptureResult`
- `normalizeIntent(rawText: string): NormalizedIntent`
- `deduplicateIntent(userId: string, normalized: NormalizedIntent): DedupDecision`

## C3 Deterministic Decision Engine
- `computeTopActions(userId: string, now: DateTime): TopActions`
- `scoreTask(task: TaskState, rules: ActiveRules, context: UserContext): ScoreBreakdown`
- `explainDecision(taskId: string, score: ScoreBreakdown): DecisionReason`

## C4 Rules Module
- `getActiveRules(scope: RuleScope): ActiveRules`
- `validateRuleChange(change: RuleChangeRequest): ValidationResult`
- `updateRules(adminUserId: string, change: RuleChangeRequest): RuleVersion`
- `listRuleVersions(scope: RuleScope): RuleVersionList`

## C5 Nudge Orchestrator
- `scheduleNudge(userId: string, action: PrioritizedAction, when: DateTime): JobId`
- `buildNudgePayload(action: PrioritizedAction): NudgePayload`
- `dispatchNudge(job: ScheduledJob): DispatchResult`

## C6 Response Handler
- `handleDone(userId: string, taskId: string, correlationId: string): ActionResult`
- `handleSnooze(userId: string, taskId: string, snoozeUntil: DateTime): ActionResult`
- `handleClarify(userId: string, taskId: string, note?: string): ActionResult`
- `applyStateTransition(command: StateTransitionCommand): StateTransitionResult`

## C7 Reporting & Rescue
- `generateDailyReport(userId: string, day: LocalDate): DailyReport`
- `detectRescueCondition(userId: string, now: DateTime): RescueDecision`
- `generateRescuePrompt(userId: string): RescuePayload`
- `sendDailyReport(userId: string, report: DailyReport): SendResult`

## C8 Loop State Store (Repository Contract)
- `getTask(taskId: string): TaskState | null`
- `listUserTasks(userId: string, filter: TaskFilter): TaskStateList`
- `upsertTaskState(state: TaskState): SaveResult`
- `applyIdempotentTransition(command: StateTransitionCommand): SaveResult`

## C9 Event Log (Repository Contract)
- `appendEvent(event: LoopEvent): AppendResult`
- `listEvents(userId: string, range: TimeRange, type?: EventType): EventList`

## C10 Admin & Access Control
- `authenticateActor(channelIdentity: ChannelIdentity): AuthResult`
- `authorizeAction(actor: ActorContext, action: AdminAction, resource?: string): AuthorizationResult`
- `assertOwnership(actor: ActorContext, taskId: string): AuthorizationResult`

## C11 Observability
- `log(level: LogLevel, message: string, fields: LogFields): void`
- `emitMetric(name: string, value: number, tags: MetricTags): void`
- `startTimer(metricName: string, tags: MetricTags): TimerHandle`

## C12 Queue Worker
- `consumeScheduledJobs(batchSize: number): ScheduledJobBatch`
- `executeJob(job: ScheduledJob): JobExecutionResult`
- `retryOrDeadLetter(job: ScheduledJob, reason: string): RetryDecision`

## Notes
- Métodos se definen a nivel de contrato; reglas de negocio detalladas se documentarán en Functional Design.
- Todas las mutaciones relevantes deben producir evento mínimo de auditoría (best effort según decisión actual).
