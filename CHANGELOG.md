# Changelog — PPAI (Personal Productivity AI)

Formato: [Keep a Changelog](https://keepachangelog.com/es/1.0.0/)
Versionado: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]

> Cambios en progreso que aún no tienen versión asignada.

---

## [v1.2.1] — 2026-03-28

### 🐛 Fixed

- Migrado flujo OAuth de Google Calendar de **Device Flow** (tipo "TV y entrada limitada") a **Desktop App** — el device flow no permite el scope `calendar.events` (escritura), solo `calendar.readonly`. Sin este fix, PPAI no podía crear eventos `[PPAI]` en el calendario del usuario.
- Nuevo flujo para el usuario: `/calendar` muestra un link de autorización → el usuario autoriza en Google → copia el código de la URL de redirección → lo pega en Telegram. Reemplaza el flujo anterior de "ingresa código en google.com/device → escribe listo".
- Reemplazados `start_device_flow()` y `poll_device_token()` por `generate_auth_url()` y `exchange_code()` en `GoogleOAuthService` — usando `requests.post` directo al token endpoint con `authorization_code` grant y `redirect_uri=http://localhost`.
- Verificado con test directo contra endpoints de Google: auth URL acepta ambos scopes (`calendar.readonly` + `calendar.events`), token endpoint acepta el client tipo Desktop para `authorization_code` grant.

---

## [v1.2.0] — 2026-03-28

### ✨ Added — ER4 LLM como Cerebro del Asistente (HU-R4.1 → HU-R4.4)

- Implementado módulo completo `ppai/intelligence/` con arquitectura hexagonal (domain, application, infrastructure).
- Implementada **captura inteligente de tareas con LLM** (HU-R4.1): al capturar una tarea, Claude Haiku analiza el texto junto con la ocupación del usuario y devuelve título normalizado, categoría, tiempo estimado y urgencia. Si la API falla o el rate limit se alcanza, el sistema usa automáticamente el clasificador regex como fallback silencioso.
- Implementados **mensajes con personalidad generados por LLM** (HU-R4.2): los mensajes de inicio de día, cierre y nudges se generan dinámicamente con Claude — Sonnet para matutino/cierre (calidad), Haiku para nudges (costo). Respetan frases prohibidas (`debías`, `ya vas tarde`, etc.) y máximo 150 palabras. Fallback silencioso a templates estáticos si la API falla.
- Implementado **análisis inteligente de fricción con estrategias personalizadas** (HU-R4.3, DIFERENCIAL): cuando el friction detector identifica una tarea estancada (3+ días), Claude Sonnet recibe el historial completo y genera diagnóstico probable, 3 estrategias concretas al contexto del usuario y 1 micro-acción de máximo 15 minutos. Incluye friction_notes previas para no repetir sugerencias. Fallback a opciones estáticas de HU-R3.3.
- Implementado **reporte semanal enriquecido con insights de LLM** (HU-R4.4, DIFERENCIAL): Claude Sonnet analiza los datos agregados de la semana y genera qué salió bien, 1 patrón problemático, 1 sugerencia concreta y 1 pregunta reflexiva — todo con datos específicos, no genéricos. Fallback al reporte estático de HU-R3.4.
- Implementado `AnthropicAdapter` como wrapper del SDK de Anthropic con soporte para respuestas JSON (`ask_json`) y texto libre (`ask_text`), con manejo de errores y timeouts.
- Implementados prompt templates especializados por caso de uso en `prompt_templates.py` con reglas de tono, frases prohibidas y formato de respuesta.
- Implementado **rate limiter diario global** (`LLMRateLimiter`): cap configurable (default 50 calls/día) que se resetea a medianoche UTC. Al exceder el cap, todas las llamadas LLM caen a fallback silencioso. Contribuye al presupuesto máximo de $20/mes.

### ⚙️ Infra

- Agregada dependencia `anthropic==0.52.0` a `requirements.txt`.
- Extendido `Settings` con `anthropic_api_key` y `llm_daily_cap` — la capa LLM se activa solo si la API key está configurada.
- Pipeline CI/CD actualizado para inyectar `ANTHROPIC_API_KEY` como secret de Terraform al contenedor ECS.
- Extendidas variables de Terraform en root, módulo ECS y container definition para `anthropic_api_key`.
- Modelos por caso de uso: Haiku para captura y nudges (~$0.001/día), Sonnet para fricción y weekly (~$0.08/día). Costo estimado total: ~$2.10/mes.
- Total del proyecto: **493 tests passing**, 0 failures.

---

## [v1.1.0] — 2026-03-28

### ✨ Added — ER3 Notificaciones Proactivas Inteligentes (HU-R3.1 → HU-R3.5)

- Implementado **recordatorios de inicio y cierre de bloque** (HU-R3.1): 5 minutos antes de cada bloque el bot envía recordatorio con botones [Arrancar] [+15min] [Saltar]; al terminar pregunta cómo fue con [Completé] [Más tiempo] [No avancé]. Scheduler dinámico baja a 1 minuto de intervalo cuando hay bloques activos.
- Implementado **detector de huecos por cambios en calendario** (HU-R3.2): cada 15 minutos compara snapshot de Google Calendar, detecta eventos cancelados/movidos y propone reasignar tarea urgente, continuar en progreso o descanso.
- Implementado **detector de fricción en tareas estancadas** (HU-R3.3, DIFERENCIAL): si una tarea lleva 3+ días en el Top 3 sin completarse, el bot ofrece 4 opciones — dividirla, pedir info, eliminarla o hacer Pomodoro de 25 minutos. `handle_divide()` crea sub-tareas y cierra la original; `handle_pomodoro()` agenda bloque inmediato.
- Implementado **reporte semanal con insights accionables** (HU-R3.4, DIFERENCIAL): cada domingo (o lunes si weekend_mode=rest) envía resumen de 7 días con tareas completadas/pospuestas, bloques completados vs planeados, día más/menos productivo, patrones detectados y sugerencias concretas para la próxima semana.
- Implementado **check-in de medio día** (HU-R3.5): si a mitad de la jornada no se ha completado ningún bloque, el bot ofrece 4 opciones de recuperación — replannear tarde, capturar imprevistos, pedir ayuda o arrancar ahora.
- Extendido `TaskState` con campos `days_in_top3` y `friction_notes` para tracking de procrastinación.
- `DecisionService` incrementa `days_in_top3` automáticamente cada vez que una tarea entra al Top 3.
- `ER3CallbackAdapter` centraliza 16 nuevos patrones de callback para los 5 tipos de notificación.
- Todas las notificaciones adaptan tono al `communication_style` del perfil (gentle/direct/confrontational) con fallback neutro.

### ⚙️ Infra

- `NudgeScheduler` con intervalo dinámico: 1 minuto cuando hay bloques activos, 5 minutos base.
- `TelegramPushAdapter` extendido con `send_message_with_buttons()` para mensajes con teclado inline.
- Actualizado `docs/infra-snapshot.md` con estado post-deploy ER1+ER2 (8 tablas DynamoDB, task def :14).
- Total del proyecto: **466 tests passing**, 0 failures.

---

## [v1.0.0] — 2026-03-28

### ✨ Added — ER1 Onboarding y Perfil de Usuario (HU-R1.1 → HU-R1.4)

- Implementado módulo completo `ppai/profile/` con arquitectura hexagonal (domain, application, infrastructure).
- Implementado **flujo de onboarding conversacional** multi-paso con `ConversationHandler`: al enviar el primer mensaje, PPAI guía al usuario por nombre, ocupación, horario laboral, bloques protegidos y estilo de comunicación. Si el usuario abandona, retoma donde se quedó. (#14)
- Implementada **persistencia de perfil** en nueva tabla DynamoDB `ppai-user-profiles`: consulta con `/perfil`, modificación individual con `/config nombre|estilo|horario|pais|finde`.
- Implementado **soporte de festivos y días libres**: festivos automáticos por país vía librería `holidays`, modo de fin de semana configurable (descanso/personal/mixto), días libres personalizados con `/libre`.
- Implementada **personalización del tono** en todos los mensajes existentes del bot (daily start, daily end, nudges, rescue): 3 variantes (gentle/direct/confrontational) adaptadas al `communication_style` del perfil. Fallback a tono neutro si no hay perfil.
- Comando `/setup` permite re-ejecutar el onboarding completo en cualquier momento con confirmación antes de sobreescribir.

### ✨ Added — ER2 Google Calendar y Bloques de Tiempo (HU-R2.1 → HU-R2.5)

- Implementado módulo completo `ppai/calendar/` con arquitectura hexagonal (domain, application, infrastructure).
- Implementada **conexión con Google Calendar vía OAuth 2.0**: comando `/calendar` devuelve enlace de autorización, usuario pega el código, bot confirma conexión mostrando próximos 3 eventos. (#14)
- Implementada **persistencia segura de tokens**: access y refresh tokens encriptados con Fernet (clave simétrica en env var `FERNET_ENCRYPTION_KEY`), renovación automática si expira, notificación si se revoca.
- Implementado **BlockPlanner**: algoritmo que detecta huecos libres en el calendario, asigna tareas priorizadas a esos huecos respetando horario laboral, bloques protegidos y categoría de tarea, con buffer de 10 minutos entre bloques y soporte para dividir tareas grandes.
- Implementada **categorización automática de tareas**: `CategoryClassifier` con 6 categorías (work, personal, learning, health, social, errand) por keywords y override con hashtag (#work, #personal, etc.). Campo `estimated_minutes` con detección de patrones temporales.
- Implementada **creación de eventos en Google Calendar**: al confirmar plan, se crean eventos con prefijo `[PPAI]`. Sync best-effort que no bloquea si Calendar falla.
- Implementados comandos `/plan` (plan de hoy con bloques e inline buttons) y `/plan tomorrow`. Callbacks `block_done`/`block_skip` para gestionar bloques desde Telegram.
- Extendido `TaskState` con campos `category` y `estimated_minutes` — backward compatible con tareas existentes.

### ⚙️ Infra

- Agregadas 3 tablas DynamoDB nuevas en Terraform: `ppai-user-profiles` (ER1), `ppai-calendar-auth` (ER2, con cifrado en reposo), `ppai-time-blocks` (ER2, PK: userId, SK: date#blockId).
- Extendido IAM Task Role con permisos para las 3 tablas nuevas (least privilege): GetItem, PutItem, UpdateItem para profiles; + DeleteItem para auth tokens; + Query y BatchWriteItem para time blocks.
- Pipeline CI/CD actualizado para inyectar 3 nuevos secrets: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `FERNET_ENCRYPTION_KEY` como variables de Terraform al contenedor ECS.
- Actualizado `.env.example` con sección de Google Calendar y comando para generar clave Fernet.
- Agregadas 5 dependencias: `holidays`, `google-auth`, `google-auth-oauthlib`, `google-api-python-client`, `cryptography`.
- Total del proyecto: **466 tests passing**, 0 failures.

---

## [v0.9.0] — 2026-03-27

### ✨ Added — UOW-05 Scheduler Bot Nativo

- Implementado **scheduler bot nativo** orientado a dos momentos del día: recordatorio de inicio y resumen de cierre, en lugar de depender solo de nudges regulares por tick.
- Implementado **recordatorio matutino automático** con Top 3 y mensaje motivacional configurable por usuario (`dailyStartTime`, `motivationalMessage`).
- Implementado **resumen de cierre del día** con listas detalladas de tareas completadas, pendientes y pospuestas.
- Implementado **Rescue Mode** para "día caído": si no hubo completadas y todavía quedan tareas, el cierre incluye una propuesta empática con microacción concreta. Se registra evento `RESCUE_TRIGGERED`.
- Implementado **modo zen nativo** vía comando `/zen` y `/zen off`: activa una sesión temporal con nudges frecuentes, cap configurable e ignorando la ventana de silencio mientras la sesión esté activa.
- Implementado **scheduler dinámico**: el intervalo del loop baja automáticamente al menor `zen_interval_minutes` entre sesiones activas y vuelve al base cuando no hay zen.
- Extendido `/config` con nuevos subcomandos:
  - `/config inicio HH:MM`
  - `/config cierre HH:MM`
  - `/config zen_intervalo N`
  - `/config zen_max N`
  - `/config motivacion TEXTO`
- Agregados componentes nuevos en la capa push:
  - `ZenSessionManager`
  - `DailySummaryBuilder`
  - `RescueEvaluator`
  - `ZenTelegramAdapter`
- Agregados **8 tests e2e** para el flujo completo de scheduler bot nativo y **6 acceptance tests BDD** para US-09 y US-10. Total del proyecto: **466 tests passing**.

### ⚙️ Infra

- Reutilizado el GSI existente `userId-status-index` en `ppai-tasks` para construir resúmenes diarios sin introducir delta de Terraform.
- Extendido `DynamoDBPreferencesRepository` con persistencia de campos UOW-05: `dailyStartTime`, `dailyEndTime`, `zenActive`, `zenIntervalMinutes`, `zenMaxNudges`, `motivationalMessage`.
- Extendido `DynamoDBCycleEventRepository` con `has_event_today()` para guards de idempotencia en `DAILY_START_SENT`, `DAILY_END_SENT` y `RESCUE_TRIGGERED`.
- Actualizado `main.py` para registrar `/zen`, reconstruir sesiones zen persistidas al arranque y cablear `NudgeService` con summary/rescue/zen.

### 🐛 Fixed

- Alineados los tests legacy de UOW-03 (`US-05`, `US-06`, `test_push_flow`) al comportamiento vigente del producto: flujo automático estándar de inicio/cierre y nudges continuos solo en modo zen.

### 📝 Docs

- Cerrados los artefactos AI-DLC de UOW-05: code summary, build-and-test summary, actualización de `aidlc-state.md`, `audit.md` y plan de code generation.
- UOW-05 queda marcado como **COMPLETO** en Construction.

---

## [v0.8.0] — 2026-03-26

### ✨ Added — UOW-04 Respond & State Transition

- Implementado flujo completo de **Done con confirmación**: al presionar `[✓ Hecho]` el bot pregunta "¿Confirmas?" con botones `[Sí] [No]` — solo al confirmar se transiciona a DONE con timestamp. (#11)
- Implementado flujo de **Snooze con cooldown**: pospone la tarea 1 hora y muestra contador `(1/3)`. Tras el cooldown, la tarea vuelve automáticamente a PENDING en el siguiente `/top3`.
- Implementado **límite de snooze** (máx 3): al intentar un 4to snooze el bot responde "Ya pospusiste esta tarea 3 veces" y activa automáticamente el flujo de aclaración.
- Implementado flujo de **Clarify con texto libre**: al presionar `[? Aclarar]` el bot pregunta qué necesita el usuario; la respuesta en texto libre actualiza la tarea y la devuelve a PENDING con snooze_count reseteado.
- Implementado registro de **InteractionEvents** (`TASK_DONE`, `TASK_SNOOZED`, `TASK_CLARIFIED`, `TASK_CLARIFY_RESOLVED`) en tabla `ppai-events` con TTL de 90 días + eventos duales en `ppai-cycles` para agregación diaria.
- Implementados **guards de idempotencia**: callbacks duplicados devuelven mensajes informativos sin cambiar estado (ej. "Esta tarea ya fue completada").
- Implementado **guard de autorización**: valida que el usuario que presiona un botón sea el dueño de la tarea — si no coincide, responde "No tienes permiso para esta acción".
- Implementado **auto-unsnoze**: al consultar `/top3`, las tareas con cooldown expirado se transicionan automáticamente de SNOOZED a PENDING.
- Nuevo paquete `ppai/respond/` con arquitectura hexagonal: domain (entities, value objects, exceptions), application (ports, ResponseService), infrastructure (DynamoDB adapter, Telegram adapter).
- 75 tests nuevos: 52 unitarios (domain + service + adapter), 12 BDD acceptance (US-07, US-08), 4 integración (DynamoDB), 7 e2e. Total: 355 tests passing.

### ⚙️ Infra

- Habilitado TTL en tabla DynamoDB `ppai-events` en Terraform — InteractionEvents se auto-eliminan a los 90 días.
- Extendido `TaskState` con campos `snoozed_until` y `completed_at` — backward compatible con tareas existentes.
- Extendido `DynamoDBTaskStateRepository` con métodos `list_by_status`, `list_snoozed` y serialización de nuevos campos.
- Wiring actualizado en `main.py`: `ResponseService` + `ResponseTelegramAdapter` conectados; callbacks extendidos con `confirm_done:` y `cancel_done:`; `MessageHandler` group=1 para respuestas de aclaración por texto libre.

### 📝 Docs

- Generados artefactos AI-DLC completos: functional design (business rules, domain entities, logic model), NFR requirements, NFR design, infrastructure design, code generation plan y summary.
- Actualizado `aidlc-state.md`: UOW-04 Code Generation completo, 355 tests, pendiente deploy a prod.

---

## [v0.7.0] — 2026-03-26

### ✨ Added

- Implementado `UserRegistry` thread-safe que registra automáticamente el `chat_id` de cada usuario al capturar tareas o usar `/top3` — el `NudgeScheduler` ahora tiene usuarios reales a quiénes evaluar en cada tick. (#10)
- Implementado comando `/config` en Telegram para que el usuario configure sus preferencias de nudge desde el chat:
  - `/config` — muestra configuración actual (timezone, máx nudges, ventana de silencio)
  - `/config silencio HH:MM-HH:MM` — configura ventana de silencio (ej. 22:00-08:00)
  - `/config nudges N` — máximo de recordatorios por día (1-10)
  - `/config timezone ZONA` — zona horaria (ej. America/Bogota)
- Conectado el scheduler con el registry: el bot ahora envía nudges proactivos a usuarios que han interactuado, respetando sus preferencias configuradas.
- 18 tests nuevos: 6 para `UserRegistry` (incluyendo thread-safety) y 12 para `ConfigTelegramAdapter` (validaciones, subcomandos, defaults). Total: 266 tests passing.

### ⚙️ Infra

- Wiring actualizado en `main.py`: `UserRegistry` inyectado en `TelegramAdapter` y `DecisionTelegramAdapter`, `ConfigTelegramAdapter` registrado como handler de `/config`, `NudgeScheduler` conectado a `registry.get_all`.

---

## [v0.6.1] — 2026-03-25

### 🐛 Fixed

- Corregido bug donde `/top3` mostraba "bandeja vacía" tras expirar el cache de 60s, cuando la tarea ya estaba como `prioritized` en DynamoDB — ahora re-muestra tareas priorizadas sin cambiar su estado. (#8)
- Corregido crash del contenedor ECS al arrancar por dependencia `requests` no declarada en `requirements.txt` — usada por `TelegramPushAdapter` (UOW-03).

---

## [v0.6.0] — 2026-03-25

### ✨ Added — UOW-03 Push & Scheduling

- Implementado scheduler in-process (`NudgeScheduler`) que cada 15 minutos evalúa usuarios activos y envía nudges proactivos por Telegram con botones inline `[✓ Hecho] [⏸ Posponer] [? Aclarar]`.
- Implementado `NudgeService` con 6 guards de negocio: ventana de silencio configurable (silenceStart/silenceEnd), cap diario de nudges (`maxNudgesPerDay`), re-engagement tras 24h de inactividad, retry hasta 3 intentos con back-off, mensaje de tone positivo sin frases prohibidas y validación de autorización de callback.
- Agregada entidad `UserNudgePreferences` con timezone, silenceStart/silenceEnd y maxNudgesPerDay — persistida en nueva tabla DynamoDB `ppai-preferences`.
- Implementado `DynamoDBPreferencesRepository` (PK: `userId`) para persistir y recuperar preferencias de nudge por usuario.
- Implementado `DynamoDBCycleEventRepository` que extiende la tabla `ppai-cycles` para registrar eventos de nudge: `nudge.scheduled`, `nudge.sent`, `nudge.failed` — con conteo diario de nudges enviados.
- Implementado `TelegramPushAdapter` que construye y envía mensajes de nudge via `sendMessage` con teclado inline de 3 botones por tarea, y valida que el callback pertenezca al usuario correcto.
- Wiring completo en `main.py`: `NudgeService` + `NudgeScheduler` conectados con todos los repositorios y el servicio de decisión.
- 94 tests nuevos: 71 unitarios (domain, nudge_service, nudge_scheduler, telegram_push_adapter), 14 de integración contra LocalStack, 9 e2e.
- 11 tests de aceptación BDD (Gherkin) para US-05 y US-06 en `tests/unit/e3/`.

### ⚙️ Infra

- Agregada tabla DynamoDB `ppai-preferences` en Terraform con PK `userId`, cifrado en reposo, deletion protection y tag `Unit: uow-03`.
- Extendido IAM Task Role con permisos `GetItem`, `PutItem` sobre `ppai-preferences` (least privilege).
- Actualizado `terraform/main.tf` con wiring de `preferences_table_arn` al módulo IAM.
- Agregada tabla `ppai-preferences` al script `scripts/create-local-tables.py` para LocalStack.

### 📝 Docs

- Actualizado `aidlc-state.md`: UOW-03 Build and Test en progreso, 262 tests passing.
- Generados artefactos AI-DLC: infrastructure design, deployment architecture y code generation summary para UOW-03.

---

## [v0.5.0] — 2026-03-23

### ⚙️ Infra

- Creado bucket S3 `ppai-terraform-state` con versioning y cifrado AES-256 como backend remoto de Terraform para estado compartido y auditable.
- Creada tabla DynamoDB `ppai-terraform-lock` (PAY_PER_REQUEST) para locking del estado de Terraform y evitar applies concurrentes.
- Configurado OIDC Identity Provider de GitHub Actions en IAM — permite que el pipeline asuma roles AWS sin credenciales de larga duración en Secrets.
- Creado rol IAM `ppai-github-deploy` con trust policy restringida al repositorio `amondrave/PPAI-Agent` para deploy desde GitHub Actions.
- Configurados GitHub Secrets `AWS_DEPLOY_ROLE_ARN` y `TELEGRAM_BOT_TOKEN` en el repositorio — pipeline CI/CD listo para activarse en el próximo push a `main`.

### 🐛 Fixed

- Corregido error en tests de ciclos que fallaban por desface de timezone: `get_top3` ahora acepta parámetro `now` inyectable con `datetime.now(timezone.utc)`.
- Corregido pipeline CI que fallaba por ausencia de dependencias de testing: agregado `requirements-dev.txt` con `pytest`, `moto`, `pytest-asyncio`.

### 📝 Docs

- Auditado y cerrado estado AI-DLC: UOW-01 y UOW-02 Build and Test marcados como COMPLETO con evidencia de CI verde y prueba manual Telegram OK.

---

## [v0.4.0] — 2026-03-21

### ✨ Added

- Entorno de desarrollo local completo con LocalStack 3.4 via `docker-compose up -d` — permite probar captura y Top 3 sin cuenta AWS.
- Script `scripts/create-local-tables.py` que crea las 4 tablas DynamoDB (`ppai-tasks`, `ppai-events`, `ppai-dedup`, `ppai-cycles`) con sus GSIs en LocalStack al iniciar.
- Entry point `ppai/local.py` en modo polling para desarrollo local — sin necesidad de URL pública ni webhook.
- Archivo `.env.example` documentado con todos los parámetros de configuración por ambiente (local vs prod).

### ⚙️ Infra

- Pipeline CI/CD completo en GitHub Actions (`.github/workflows/deploy.yml`) con 4 jobs: `test → build-push → terraform → deploy`. Solo despliega en push a `main`.
- OIDC provider IAM + `ppai-github-deploy-role` en Terraform (`iam/github-oidc.tf`) — GitHub Actions asume el role sin credenciales de larga duración en Secrets.
- Permisos mínimos para el deploy role: ECR, ECS, S3 (state), DynamoDB (lock), IAM, CloudWatch Logs.

### 🐛 Fixed

- Corregido error de arranque del bot al leer `.env` con variables `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — pydantic-settings configurado con `extra="ignore"` para ignorar variables no declaradas en el modelo.

---

## [v0.3.0] — 2026-03-21

### ✨ Added — UOW-02 Decision Core

- Implementado motor de priorización Top 3 determinístico (`ScoringEngine`) con tres factores: urgencia por deadline, antigüedad en pending y conteo de posposiciones. Score máximo posible: 27 puntos.
- Agregada entidad `ExecutionCycle` para agrupar eventos de decisión por usuario por día, con soporte de fallback si el scheduler (UOW-03) aún no existe.
- Agregados value objects `PriorityScore` y `Top3Result` — computados en memoria, nunca persistidos directamente.
- Implementado `DecisionService` con los flujos principales: `get_top3`, `clarify` y `reorder`. Cache in-process con TTL de 60 segundos para evitar queries repetidos a DynamoDB.
- Implementado handler `/top3` en Telegram con presentación por mensaje individual por tarea + botones inline `[✓ Hecho] [⏸ Posponer] [? Aclarar]`.
- Implementado `CallbackQueryHandler` para acciones sobre tareas del Top 3 vía botones inline — formato `{action}:{task_id}`.
- Agregado repositorio DynamoDB `DynamoDBCycleRepository` para tabla `ppai-cycles` con GSI `userId-date-index`.
- Conectados UOW-01 y UOW-02: al capturar una tarea nueva, se invalida automáticamente el cache del Top 3 del usuario.
- Agregado campo `snooze_count` (default 0) en la entidad `TaskState` — backward compatible con tareas existentes.
- Agregado status `NEEDS_CLARIFICATION` al enum `TaskStatus`.
- Agregado método `list_pending` en `DynamoDBTaskStateRepository` usando el GSI `userId-status-index` existente.
- 93 tests nuevos: 65 unitarios, 14 de integración (moto), 14 e2e.

### ⚙️ Infra

- Agregada tabla DynamoDB `ppai-cycles` en Terraform con GSI `userId-date-index`, encryption habilitado y deletion protection.
- Extendido IAM Task Role con permisos `PutItem`, `GetItem`, `UpdateItem`, `Query` sobre `ppai-cycles` y su índice (least privilege).
- Actualizado `main.tf` raíz para pasar `cycles_table_arn` al módulo IAM.

### 📝 Docs

- Generado Code Plan UOW-02 (`aidlc-docs/construction/plans/decision-core-code-plan.md`) con 12 steps, tabla de Linear Issues y estrategia de GitHub Actions + OIDC para prod.
- Actualizado `aidlc-state.md` con progreso UOW-02 completo y próximos pasos.

---

## [v0.2.0] — 2026-03-17

### ✨ Added — UOW-01 Capture Foundation

- Implementada capa de dominio completa: entidades `Intent`, `TaskState`, `CaptureEvent`, `DedupRecord`; enum `TaskStatus` con 7 estados; jerarquía de excepciones `CaptureError`.
- Implementada capa de aplicación: puertos (`TaskStateRepository`, `EventRepository`, `DedupRepository`), `CaptureService` con 10 reglas de negocio (BR-CAP-01..10) — normalización, extracción de tags, deadlines relativos, deduplicación, límite de tareas activas.
- Implementada capa de infraestructura: `DynamoDBTaskStateRepository`, `DynamoDBEventRepository`, `DynamoDBDedupRepository` (con TTL configurable), adapter de Telegram para captura de texto libre, rate limiter in-memory con ventana deslizante, logging estructurado con structlog.
- Implementado entry point `main.py` en modo webhook (puerto 8443).
- Infraestructura completa en Terraform (7 módulos): VPC, ECS Fargate, ECR, DynamoDB (3 tablas + GSIs), IAM con least privilege, API Gateway HTTP, CloudWatch Log Groups.
- Dockerfile multi-stage optimizado para producción en ECS Fargate.
- 75 tests: 52 unitarios (domain + service), 14 de integración (DynamoDB con moto), 9 e2e (flujo Telegram simulado).

### ⚙️ Infra

- Módulos Terraform: `networking`, `dynamodb`, `ecr`, `iam`, `ecs`, `api-gateway`, `monitoring`.
- Tablas DynamoDB con billing On-Demand, deletion protection, GSI `userId-status-index` en `ppai-tasks`.
- VPC endpoints para DynamoDB (tráfico interno, sin NAT para DB calls).

### 📝 Docs

- Workflow AI-DLC documentado en `AI_DLC_WORKFLOW.md` con fases Inception, Construction y Operations.
- Documentación de diseño UOW-01: functional design, NFR requirements, NFR design, infrastructure design.
- Guía de setup completa (`docs/setup-guide.md`): configuración Telegram, LocalStack, deploy AWS.

---

## [v0.1.0] — 2026-03-09

### ✨ Added — Fundación del proyecto

- PRD v1.0 consolidado (`specs/prd.md`) con visión del producto, user stories y criterios de aceptación.
- Backlog inicial generado desde PRD con épicas y stories priorizadas.
- MCPs configurados en `.mcp.json`: `filesystem`, `github`, `sqlite`, `linear`.

### ⚙️ Infra

- Skills disponibles: `prd-to-backlog`, `story-to-bdd`, `changelog`, `aidlc-to-linear`.
- Workflow AI-DLC (AI-Driven Development Lifecycle) definido como metodología del proyecto.
- Estructura de carpetas del repositorio: `specs/`, `aidlc-docs/`, `ppai/`, `terraform/`, `tests/`, `docs/`.

### 📝 Docs

- `CLAUDE.md` con instrucciones del proyecto para Claude Code.
- Documentación de fases Inception completas: Requirements Analysis, User Stories, Workflow Planning, Application Design, Units Planning.

---

[Unreleased]: https://github.com/amondrave/PPAI-Agent/compare/v1.2.1...HEAD
[v1.2.1]: https://github.com/amondrave/PPAI-Agent/compare/v1.2.0...v1.2.1
[v1.2.0]: https://github.com/amondrave/PPAI-Agent/compare/v1.1.0...v1.2.0
[v1.1.0]: https://github.com/amondrave/PPAI-Agent/compare/v1.0.0...v1.1.0
[v1.0.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.9.0...v1.0.0
[v0.9.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.8.0...v0.9.0
[v0.8.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.7.0...v0.8.0
[v0.7.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.6.1...v0.7.0
[v0.6.1]: https://github.com/amondrave/PPAI-Agent/compare/v0.6.0...v0.6.1
[v0.6.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.5.0...v0.6.0
[v0.5.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.4.0...v0.5.0
[v0.4.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.3.0...v0.4.0
[v0.3.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.2.0...v0.3.0
[v0.2.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.1.0...v0.2.0
[v0.1.0]: https://github.com/amondrave/PPAI-Agent/releases/tag/v0.1.0
