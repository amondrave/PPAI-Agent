# Backlog de Refactor — PPAI v2.0

Generado desde: `REFACTOR_PLAN.md`
Fecha de generación: 2026-03-27
Estado: Draft v1.0
Generado por: Skill refactor-to-backlog v1.0

> Este backlog complementa el backlog original (`specs/backlog.md`) del MVP.
> Las épicas ER1-ER4 son nuevas funcionalidades de refactor, no reemplazan E1-E7.

> Convenciones:
> - Idioma: español para negocio, inglés para nombres técnicos y código
> - Prioridad: P1-crítico · P2-importante · P3-deseable
> - Prefijo ER = Épica de Refactor (diferenciar de E1-E7 del MVP)
> - Prefijo HU-R = Historia de Usuario de Refactor

---

## Índice de épicas de refactor

| ID | Épica | HUs | UOW-R | Prioridad | Depende de |
|----|-------|-----|-------|-----------|------------|
| ER1 | Onboarding y Perfil de Usuario | HU-R1.1 · HU-R1.2 · HU-R1.3 · HU-R1.4 · HU-R1.5 | UOW-R1 | P1 | — |
| ER2 | Google Calendar y Bloques de Tiempo | HU-R2.1 · HU-R2.2 · HU-R2.3 · HU-R2.4 · HU-R2.5 | UOW-R2 | P1 | — |
| ER3 | Notificaciones Proactivas Inteligentes | HU-R3.1 · HU-R3.2 · HU-R3.3 · HU-R3.4 · HU-R3.5 | UOW-R3 | P1 | ER1, ER2 |
| ER4 | LLM como Cerebro del Asistente | HU-R4.1 · HU-R4.2 · HU-R4.3 · HU-R4.4 | UOW-R4 | P2 | ER1 |
| ER5 | Captura con Asignación Directa a Calendar | HU-R5.1 · HU-R5.2 · HU-R5.3 | UOW-R5 | P1 | ER1, ER2 |

---

## Mapa de dependencias

```
ER1 (Perfil) ──────────┐
                        ├─→ ER3 (Notificaciones Proactivas)
ER2 (Calendar) ────────┘         │
                                  │
ER4 (LLM) ──────────────────────┘
                                  │
ER5 (Captura→Calendar) ─────────┘ (depende de ER1 + ER2)
```

> ER1 y ER2 son independientes y pueden ejecutarse en paralelo.
> ER3 requiere ambos (perfil para tono + bloques para reminders).
> ER4 puede iniciar en paralelo con ER3 (captura inteligente no depende de bloques).

---

## ER1 — Onboarding y Perfil de Usuario

> **UOW-R:** UOW-R1
> **Objetivo:** Que PPAI conozca al usuario (nombre, ocupación, horarios, estilo de comunicación, días libres) para personalizar toda la experiencia.
> **Estimación:** 12-14 steps de code generation

---

### HU-R1.1 — Flujo de onboarding conversacional

**Como** usuario nuevo de PPAI
**Quiero** que el bot me guíe en una conversación paso a paso para configurar mi perfil (nombre, ocupación, horario laboral, bloques protegidos y estilo de comunicación)
**Para** que PPAI me conozca y personalice los mensajes, horarios y tono desde el primer día

**Prioridad:** P1-crítico
**UOW-R:** UOW-R1
**Dependencias:** Ninguna

**Acceptance Criteria:**
- [ ] AC: Al enviar el primer mensaje a PPAI, si no existe un perfil completado para el usuario, el bot inicia automáticamente el flujo de onboarding antes de capturar tareas.
- [ ] AC: El flujo solicita en orden: nombre, ocupación, hora de inicio de jornada, hora de fin de jornada, bloques protegidos (opcional) y estilo de comunicación (gentil/directo/confrontacional).
- [ ] AC: Si el usuario abandona el onboarding a mitad de camino (deja de responder), PPAI retoma donde se quedó en la siguiente interacción.
- [ ] AC: Al finalizar, el bot muestra un resumen del perfil y pide confirmación explícita antes de guardar.
- [ ] AC: El comando `/setup` permite re-ejecutar el onboarding completo en cualquier momento, sobreescribiendo el perfil anterior con confirmación.

**Notas Técnicas:**
- Archivos: `ppai/profile/domain/entities.py`, `ppai/profile/domain/value_objects.py`, `ppai/profile/application/onboarding_service.py`, `ppai/profile/infrastructure/onboarding_telegram_adapter.py`, `ppai/main.py`
- Modelo de datos: `UserProfile` (nueva entidad) con campos: `name`, `occupation`, `work_start`, `work_end`, `protected_blocks`, `communication_style`, `timezone`
- Servicios externos: Ninguno
- Consideraciones: El onboarding debe usar `ConversationHandler` de python-telegram-bot para manejar el flujo multi-paso. El estado conversacional vive en memoria (no persiste entre reinicios del bot).

---

### HU-R1.2 — Persistencia y gestión del perfil de usuario

**Como** usuario de PPAI
**Quiero** que mi perfil se guarde de forma segura y pueda consultarlo o modificar datos puntuales sin repetir todo el onboarding
**Para** mantener mi información actualizada sin fricción

**Prioridad:** P1-crítico
**UOW-R:** UOW-R1
**Dependencias:** HU-R1.1

**Acceptance Criteria:**
- [ ] AC: El perfil del usuario se persiste en DynamoDB y sobrevive reinicios del bot y redeploys.
- [ ] AC: El usuario puede consultar su perfil con `/perfil` y ver un resumen de todos sus datos configurados.
- [ ] AC: El usuario puede modificar datos individuales con comandos como `/config nombre Angel`, `/config estilo directo`, `/config horario 08:00-17:00` sin repetir el onboarding completo.
- [ ] AC: Los campos `timezone` y horarios que hoy viven en `ppai-preferences` se migran automáticamente al perfil cuando el usuario completa el onboarding, sin perder datos existentes.
- [ ] AC: Si se intenta guardar un perfil con datos inválidos (hora de inicio posterior a hora de fin, bloques protegidos solapados), el bot rechaza el cambio con mensaje explicativo.

**Notas Técnicas:**
- Archivos: `ppai/profile/application/profile_service.py`, `ppai/profile/infrastructure/dynamodb_profile_repo.py`, `ppai/profile/domain/exceptions.py`, `terraform/modules/dynamodb/main.tf`
- Modelo de datos: Tabla `ppai-user-profiles` (PK: `userId`). Migración de `timezone` desde `ppai-preferences`.
- Servicios externos: Ninguno
- Consideraciones: La migración de timezone debe ser no-destructiva: si el usuario ya tiene preferences, el timezone se copia al perfil y se referencia desde ahí. El campo en preferences se mantiene por backward compatibility hasta que se valide que todo funciona.

---

### HU-R1.3 — Configuración de festivos, días libres y fines de semana

**Como** usuario de PPAI
**Quiero** configurar mi país (para festivos automáticos), cómo maneja PPAI los fines de semana (descanso, proyectos personales o mixto) y agregar días libres personalizados
**Para** que el bot respete mis días de descanso y no me proponga planes laborales cuando no corresponde

**Prioridad:** P2-importante
**UOW-R:** UOW-R1
**Dependencias:** HU-R1.2

**Acceptance Criteria:**
- [ ] AC: Durante el onboarding (o vía `/config pais CO`), el usuario selecciona su país y PPAI carga automáticamente los festivos nacionales del año en curso.
- [ ] AC: El usuario configura el modo de fin de semana con `/config finde descanso|personal|mixto`, y el bot ajusta su comportamiento: descanso (solo recordatorios suaves), personal (propone tareas personales/learning) o mixto (sábado libre, domingo planificación).
- [ ] AC: El usuario puede agregar y listar días libres personalizados con `/libre 2026-04-15` y `/libre list`.
- [ ] AC: En un día festivo o libre, el bot NO envía plan matutino laboral; si hay tareas personales pendientes urgentes, envía un recordatorio suave adaptado al `weekend_mode`.
- [ ] AC: El primer lunes después de un festivo/fin de semana largo, el bot incluye en el plan matutino las tareas que se acumularon durante los días libres.

**Notas Técnicas:**
- Archivos: `ppai/profile/domain/entities.py` (campos `days_off`, `holidays_country`, `weekend_mode`), `ppai/profile/application/profile_service.py`, `ppai/profile/infrastructure/onboarding_telegram_adapter.py`
- Modelo de datos: `UserProfile` extendido con `days_off: list[str]`, `holidays_country: str | None`, `weekend_mode: str`
- Servicios externos: Librería `holidays` de Python para festivos por país (no requiere API externa)
- Consideraciones: Los festivos se calculan al vuelo con la librería `holidays`, no se pre-cargan en DynamoDB. Para países no soportados, se usan los **festivos de Colombia como default** y el usuario puede agregar/quitar días manualmente.

---

### HU-R1.4 — Personalización del tono en mensajes existentes del bot

**Como** usuario de PPAI
**Quiero** que todos los mensajes que ya envía el bot (inicio de día, cierre de día, nudges, rescate) se adapten al estilo de comunicación que elegí en mi perfil
**Para** sentir que el bot me habla como yo necesito y no con un tono genérico

**Prioridad:** P1-crítico
**UOW-R:** UOW-R1
**Dependencias:** HU-R1.2

**Acceptance Criteria:**
- [ ] AC: El mensaje de inicio de día (daily start) incluye el nombre del usuario y usa el tono configurado: gentil ("Buenos días Angel, hoy tienes..."), directo ("Angel, tu plan de hoy:"), o confrontacional ("Angel, ayer no completaste X. Hoy arrancamos con eso.").
- [ ] AC: El mensaje de cierre de día adapta el tono al `communication_style`: gentil celebra cualquier avance, directo reporta datos, confrontacional confronta tareas no hechas.
- [ ] AC: Los nudges zen y el modo rescate respetan el estilo de comunicación elegido.
- [ ] AC: Si el usuario no tiene perfil (legacy o sin onboarding), los mensajes usan el tono neutro actual como fallback.
- [ ] AC: Los mensajes nunca usan frases prohibidas (`debías`, `ya vas tarde`, `otra vez`) independientemente del estilo. (contribuye a: métrica "¿Siento que PPAI me conoce?")

**Notas Técnicas:**
- Archivos: `ppai/push/application/daily_summary_builder.py`, `ppai/push/application/rescue_evaluator.py`, `ppai/push/application/nudge_service.py`, `ppai/push/infrastructure/telegram_push_adapter.py`
- Modelo de datos: Lectura de `UserProfile.communication_style` y `UserProfile.name`
- Servicios externos: Ninguno (templates estáticos por estilo, el LLM viene en ER4)
- Consideraciones: Se crean 3 variantes de cada template de mensaje (gentle/direct/confrontational). Esto es un paso intermedio antes de ER4 donde el LLM generará mensajes dinámicos. El fallback a templates estáticos siempre debe existir.

---

### HU-R1.5 — Comando /help para orientación del usuario

**Como** usuario de PPAI (nuevo o recurrente)
**Quiero** poder ejecutar `/help` y recibir una guía clara y organizada de todos los comandos disponibles, subcomandos y cómo funciona la captación de tareas
**Para** entender rápidamente qué puedo hacer con el bot sin tener que buscar documentación externa

**Prioridad:** P1-crítico
**UOW-R:** UOW-R1
**Dependencias:** Ninguna

**Acceptance Criteria:**
- [ ] AC: Al ejecutar `/help`, el bot responde con un mensaje organizado por secciones: (1) Cómo capturar tareas (texto libre, con duración, con categoría), (2) Comandos principales (`/plan`, `/top`, `/done`, `/snooze`, `/calendar`, `/perfil`, `/setup`, `/config`), (3) Subcomandos y flags disponibles por comando.
- [ ] AC: Cada comando en el listado incluye una descripción de una línea y un ejemplo de uso (ej: "`/config estilo directo` — cambia tu estilo de comunicación").
- [ ] AC: El mensaje de `/help` no supera los 4096 caracteres (límite de Telegram) y usa formato Markdown para legibilidad.
- [ ] AC: Si el usuario ejecuta `/help <comando>` (ej: `/help config`), el bot muestra la ayuda detallada solo de ese comando con todos sus subcomandos y ejemplos.
- [ ] AC: El contenido del help se actualiza automáticamente cuando se agregan nuevos comandos al bot (los handlers registrados determinan el contenido).

**Notas Técnicas:**
- Archivos: `ppai/bot/commands/help_command.py` (nuevo), `ppai/main.py` (registrar handler)
- Modelo de datos: No requiere persistencia — la información se genera a partir de los handlers registrados.
- Servicios externos: Ninguno
- Consideraciones: Evaluar si el help se genera estáticamente (diccionario de comandos) o dinámicamente inspeccionando los handlers registrados. Para V1, un diccionario estático es más confiable y controlable. Usar `parse_mode=Markdown` para formateo en Telegram.

---

---

## ER2 — Google Calendar y Bloques de Tiempo

> **UOW-R:** UOW-R2
> **Objetivo:** Integrar Google Calendar (personal) para leer eventos, detectar huecos libres, y proponer un plan del día con bloques de trabajo asignados a las tareas priorizadas.
> **Estimación:** 16-18 steps de code generation
> **Nota (Comentario Angel #1):** El calendario es siempre el personal de Google del usuario. No se accede a calendarios empresariales. El usuario refleja su jornada laboral como eventos en su calendar personal y PPAI organiza alrededor de lo que ve.

---

### HU-R2.1 — Conexión con Google Calendar vía OAuth

**Como** usuario de PPAI
**Quiero** vincular mi cuenta de Google Calendar al bot mediante un flujo simple de autorización
**Para** que PPAI pueda leer mis eventos y proponer planes basados en mi disponibilidad real

**Prioridad:** P1-crítico
**UOW-R:** UOW-R2
**Dependencias:** Ninguna

**Acceptance Criteria:**
- [ ] AC: Al ejecutar `/calendar`, el bot devuelve un enlace de autorización de Google y pide al usuario que pegue el código de verificación.
- [ ] AC: Una vez autorizado, el bot confirma la conexión y muestra los próximos 3 eventos del día como prueba de que funciona.
- [ ] AC: Los tokens de acceso y refresh se persisten de forma segura en DynamoDB (encriptados con Fernet, clave en env var) y sobreviven reinicios del bot.
- [ ] AC: Si el token expira, el bot lo renueva automáticamente usando el refresh token sin intervención del usuario.
- [ ] AC: Si el refresh token también expira o es revocado, el bot notifica al usuario que debe reconectar con `/calendar` y no falla silenciosamente.
- [ ] AC: Solo se solicitan los scopes mínimos necesarios: lectura de calendario y escritura de eventos.

**Notas Técnicas:**
- Archivos: `ppai/calendar/infrastructure/google_oauth.py`, `ppai/calendar/infrastructure/google_calendar_adapter.py`, `ppai/calendar/infrastructure/dynamodb_auth_repo.py`, `ppai/calendar/infrastructure/calendar_telegram_adapter.py`
- Modelo de datos: `UserProfile` extendido con campos `google_access_token`, `google_refresh_token`, `google_token_expiry`, `google_calendar_connected`
- Servicios externos: Google Calendar API (OAuth 2.0, scopes: `calendar.readonly`, `calendar.events`)
- Consideraciones: Usar OAuth 2.0 con flujo de dispositivo (device flow) adaptado a Telegram. Los tokens se encriptan con **Fernet** (clave simétrica en env var `GOOGLE_TOKEN_ENCRYPTION_KEY`), no KMS. Crear **proyecto dedicado "PPAI"** en Google Cloud con Calendar API habilitada + credenciales OAuth.

---

### HU-R2.2 — Planificación matutina con bloques de tiempo

**Como** usuario de PPAI con Google Calendar conectado
**Quiero** que cada mañana el bot lea mi calendario, detecte mis huecos libres, y me proponga un plan del día asignando mis tareas priorizadas a esos huecos
**Para** tener un plan concreto con horarios específicos sin tener que organizarme manualmente

**Prioridad:** P1-crítico
**UOW-R:** UOW-R2
**Dependencias:** HU-R2.1, ⚠️ Depende de: ER1/HU-R1.2 (perfil con horarios y bloques protegidos)

**Acceptance Criteria:**
- [ ] AC: Cada mañana (a `daily_start_time - 10min`), si el usuario tiene Calendar conectado, el bot envía un plan del día con bloques de tiempo específicos para cada tarea del Top 3.
- [ ] AC: El plan respeta los eventos existentes en Google Calendar (los muestra como bloques ocupados) y los bloques protegidos del perfil del usuario.
- [ ] AC: Las tareas de categoría "work" se asignan solo a huecos dentro del horario laboral; las tareas personales se asignan a huecos fuera del horario laboral.
- [ ] AC: Si una tarea no cabe completa en un hueco, se divide en múltiples bloques (ej: "HU-45" en 2 bloques de 1.5h y 2h).
- [ ] AC: El plan incluye un buffer de 10 minutos entre bloques para evitar solapamientos.
- [ ] AC: El usuario puede aceptar el plan (`sí`), ajustarlo (`ajustar` + instrucciones), o rechazarlo (`no`). (contribuye a: métrica "Bloques completados vs planeados >60%")

**Notas Técnicas:**
- Archivos: `ppai/calendar/domain/entities.py` (`TimeBlock`, `DayPlan`, `FreeSlot`), `ppai/calendar/domain/value_objects.py` (`TaskCategory`, `BlockStatus`), `ppai/calendar/application/block_planner.py`, `ppai/calendar/application/calendar_service.py`, `ppai/calendar/application/calendar_sync.py`
- Modelo de datos: Tabla `ppai-time-blocks` (PK: `userId`, SK: `date#blockId`). Lectura de `UserProfile.work_start`, `work_end`, `protected_blocks`.
- Servicios externos: Google Calendar API (lectura de eventos del día)
- Consideraciones: El `BlockPlanner` es el algoritmo más crítico. V1 debe ser simple: ordenar huecos cronológicamente, asignar tareas por prioridad y categoría, sin optimización avanzada. Cache de eventos de Calendar (refrescar cada 15 min, no cada tick del scheduler).

---

### HU-R2.3 — Creación de bloques en Google Calendar

**Como** usuario de PPAI
**Quiero** que al aceptar el plan del día, los bloques de trabajo se creen automáticamente como eventos en mi Google Calendar
**Para** ver mi día completo (reuniones + tareas) en un solo lugar y recibir las notificaciones nativas de Calendar

**Prioridad:** P2-importante
**UOW-R:** UOW-R2
**Dependencias:** HU-R2.2

**Acceptance Criteria:**
- [ ] AC: Al confirmar el plan, se crean eventos en Google Calendar para cada bloque de tarea con título "[PPAI] {nombre de la tarea}" y descripción con la categoría y tiempo estimado.
- [ ] AC: Si el usuario ajusta el plan (mueve una tarea de hora), los eventos se crean con los horarios ajustados.
- [ ] AC: Si un bloque se marca como completado o saltado en PPAI, el evento correspondiente en Calendar se actualiza (o se elimina, según preferencia del usuario).
- [ ] AC: Los bloques protegidos del perfil NO se crean como eventos (ya son del usuario).
- [ ] AC: Si la escritura en Calendar falla, el plan sigue funcionando en PPAI y se notifica al usuario que los eventos no se crearon.

**Notas Técnicas:**
- Archivos: `ppai/calendar/infrastructure/google_calendar_adapter.py` (escritura), `ppai/calendar/application/calendar_sync.py` (sync bidireccional)
- Modelo de datos: `TimeBlock.calendar_event_id` almacena el ID del evento creado en Google Calendar
- Servicios externos: Google Calendar API (escritura de eventos, scope `calendar.events`)
- Consideraciones: La escritura en Calendar es best-effort. Si falla (rate limit, token expirado), PPAI no debe fallar. Los eventos creados por PPAI deben tener un prefijo `[PPAI]` para identificarlos.

---

### HU-R2.4 — Categorización de tareas para asignación a franjas

**Como** usuario de PPAI
**Quiero** que mis tareas se clasifiquen automáticamente por categoría (trabajo, personal, aprendizaje, salud, social, diligencia) al capturarlas
**Para** que el planificador de bloques sepa en qué franja horaria ubicar cada tarea

**Prioridad:** P1-crítico
**UOW-R:** UOW-R2
**Dependencias:** Ninguna

**Acceptance Criteria:**
- [ ] AC: Al capturar una tarea, el sistema le asigna automáticamente una categoría (work, personal, learning, health, social, errand) basada en el texto y el perfil del usuario.
- [ ] AC: La categoría asignada se muestra en la confirmación de captura para que el usuario pueda corregirla si es incorrecta.
- [ ] AC: El usuario puede asignar categoría manualmente al capturar usando hashtag (ej: "llamar mamá #social") como override, y también puede corregir la categoría post-captura con un callback.
- [ ] AC: Se agrega un campo `estimated_minutes` a las tareas que se usa para calcular la duración de los bloques (si no se puede estimar, se asigna 30 minutos por defecto).
- [ ] AC: Las categorías determinísticas (regex + hashtag override) funcionan como base; la clasificación por LLM (ER4) la mejorará después sin romper el flujo. (contribuye a: métrica "Bloques completados vs planeados >60%")

**Notas Técnicas:**
- Archivos: `ppai/capture/domain/entities.py` (extensión de `TaskState` con `category`, `estimated_minutes`), `ppai/calendar/domain/value_objects.py` (`TaskCategory` enum), `ppai/capture/application/capture_service.py`
- Modelo de datos: Extensión de `ppai-tasks` con campos `category` y `estimated_minutes`
- Servicios externos: Ninguno (V1 usa regex/keywords; V2 con LLM viene en ER4)
- Consideraciones: V1 de categorización es por keywords: "HU", "sprint", "código", "deploy" → work; "llamar", "mamá", "amigo" → social; "leer", "curso", "estudiar" → learning; "gym", "correr", "médico" → health; "pagar", "comprar", "trámite" → errand. Fallback: personal.

---

### HU-R2.5 — Comandos de gestión de plan y bloques

**Como** usuario de PPAI
**Quiero** poder ver mi plan actual, regenerarlo, y marcar bloques como completados o saltados desde Telegram
**Para** interactuar con mi plan del día sin salir del bot

**Prioridad:** P2-importante
**UOW-R:** UOW-R2
**Dependencias:** HU-R2.2

**Acceptance Criteria:**
- [ ] AC: `/plan` muestra el plan del día actual con el estado de cada bloque (pendiente, en progreso, completado, saltado).
- [ ] AC: `/plan tomorrow` genera una propuesta de plan para mañana basada en las tareas pendientes y el calendario de mañana.
- [ ] AC: Los callbacks `block_done:{blockId}` y `block_skip:{blockId}` permiten marcar bloques directamente desde los botones inline del plan.
- [ ] AC: Si no hay Calendar conectado, `/plan` muestra un plan basado solo en las tareas priorizadas y los horarios del perfil, sin huecos de Calendar.
- [ ] AC: Si no hay tareas pendientes, `/plan` indica que no hay nada que planificar y sugiere capturar tareas.

**Notas Técnicas:**
- Archivos: `ppai/calendar/infrastructure/calendar_telegram_adapter.py`, `ppai/calendar/infrastructure/dynamodb_block_repo.py`, `ppai/respond/infrastructure/response_telegram_adapter.py` (nuevo callback pattern `block_done|block_skip`)
- Modelo de datos: `TimeBlock.status` transiciona: `planned → in_progress → completed|skipped`
- Servicios externos: Google Calendar API (lectura para `/plan tomorrow`)
- Consideraciones: `/plan` sin Calendar conectado es un "modo degradado" que sigue siendo útil — prioriza tareas y les asigna horas basándose solo en el horario del perfil. Esto permite que ER2 funcione parcialmente sin OAuth.

---

---

## ER3 — Notificaciones Proactivas Inteligentes

> **UOW-R:** UOW-R3
> **Objetivo:** Transformar a PPAI de reactivo (espera que el usuario escriba) a proactivo (el bot inicia la conversación con contexto), con 5 tipos de notificaciones inteligentes basadas en el perfil y los bloques del día.
> **Estimación:** 10-12 steps de code generation
> **Nota (Comentario Angel #3):** El Friction Detector y el Weekly Insight son el **diferencial principal** del producto. Máxima prioridad y calidad.

---

### HU-R3.1 — Recordatorios de inicio y cierre de bloque

**Como** usuario de PPAI con un plan del día activo
**Quiero** recibir un recordatorio 5 minutos antes de que arranque cada bloque y una pregunta de check-in cuando termine
**Para** no olvidar mis bloques planificados y registrar mi avance sobre la marcha

**Prioridad:** P1-crítico
**UOW-R:** UOW-R3
**Dependencias:** ⚠️ Depende de: ER2/HU-R2.2 (plan con bloques)

**Acceptance Criteria:**
- [ ] AC: 5 minutos antes de cada bloque, el usuario recibe un mensaje con el nombre de la tarea, duración, y botones: [Arrancar], [+15min], [Saltar].
- [ ] AC: Al terminar un bloque (hora de fin), el bot pregunta cómo le fue con botones: [Completé], [Necesito más tiempo], [No avancé].
- [ ] AC: Si elige "Necesito más tiempo", el bot busca el siguiente hueco libre y propone reagendar la tarea ahí.
- [ ] AC: Si elige "No avancé" y es estilo directo/confrontacional, el bot pregunta específicamente qué lo frenó y guarda la respuesta como `friction_note` en la tarea.
- [ ] AC: Los recordatorios respetan la ventana de silencio y el modo zen (no se solapan con nudges zen).
- [ ] AC: El intervalo del scheduler se reduce a 1 minuto cuando hay bloques activos en el día, para precisión en los reminders. (contribuye a: métrica "Interacciones iniciadas por bot 70%/30%")

**Notas Técnicas:**
- Archivos: `ppai/push/application/nudge_scheduler.py` (extensión del `_tick()` con `_evaluate_block_reminders` y `_evaluate_block_checkins`), `ppai/push/application/block_checkin.py` (nuevo), `ppai/respond/infrastructure/response_telegram_adapter.py` (nuevos callbacks)
- Modelo de datos: Lectura de `ppai-time-blocks`. Nuevos eventos en `ppai-events`: `BLOCK_REMINDER_SENT`, `BLOCK_CHECKIN_SENT`, `BLOCK_COMPLETED`, `BLOCK_SKIPPED`.
- Servicios externos: Ninguno
- Consideraciones: El scheduler pasa de floor 5min a 1min cuando hay bloques activos. Esto no genera carga significativa (query por PK a DynamoDB = O(1)). Guard de no re-enviar: verificar `BLOCK_REMINDER_SENT` antes de disparar.

---

### HU-R3.2 — Detector de huecos por cambios en calendario

**Como** usuario de PPAI
**Quiero** que si una reunión se cancela o se mueve en mi Google Calendar, el bot detecte el hueco nuevo y me proponga cómo aprovecharlo
**Para** no perder tiempo libre inesperado y reasignar tareas pendientes

**Prioridad:** P3-deseable
**UOW-R:** UOW-R3
**Dependencias:** ⚠️ Depende de: ER2/HU-R2.1 (Calendar conectado), ER2/HU-R2.2 (bloques)

**Acceptance Criteria:**
- [ ] AC: Cada 15 minutos, el bot compara los eventos actuales de Google Calendar con el plan generado al inicio del día.
- [ ] AC: Si detecta un hueco nuevo (evento cancelado o movido), envía una notificación con opciones: reasignar la tarea más urgente, continuar una tarea en progreso, o tomar descanso.
- [ ] AC: Si el usuario no responde en 10 minutos, el bot no insiste (el hueco puede ser intencional).
- [ ] AC: El detector no se activa en días libres ni fines de semana en modo descanso.

**Notas Técnicas:**
- Archivos: `ppai/push/application/gap_detector.py` (nuevo), `ppai/calendar/application/calendar_sync.py` (comparación de snapshots)
- Modelo de datos: Cache in-memory del snapshot de Calendar del día. Comparación con estado anterior.
- Servicios externos: Google Calendar API (lectura periódica)
- Consideraciones: Para evitar rate limits, se cachean los eventos del día y se refrescan cada 15 minutos (no cada tick). Si Calendar no está conectado, este detector no se activa.

---

### HU-R3.3 — Detector de fricción en tareas estancadas

**Como** usuario de PPAI
**Quiero** que cuando una tarea lleve 3 o más días apareciendo en mi Top 3 sin completarse, el bot me confronte directamente con opciones para desbloquearla
**Para** identificar y romper el patrón de procrastinación en tareas específicas en lugar de seguir posponiéndolas

**Prioridad:** P1-crítico (DIFERENCIAL DEL PRODUCTO)
**UOW-R:** UOW-R3
**Dependencias:** ⚠️ Depende de: ER1/HU-R1.4 (tono personalizado)

**Acceptance Criteria:**
- [ ] AC: Si una tarea lleva 3+ días en el Top 3 sin pasar a estado DONE, el bot envía una notificación de fricción durante el plan matutino.
- [ ] AC: La notificación ofrece exactamente 4 opciones: (1) dividirla porque es muy grande, (2) pedir contexto/información que falta, (3) eliminarla porque no es importante, (4) hacer un Pomodoro de 25 minutos ahora.
- [ ] AC: Si el usuario elige "dividirla", el bot pregunta en cuántas partes y pide una descripción breve de cada sub-parte, creando tareas nuevas y marcando la original como resuelta.
- [ ] AC: Si el usuario elige "Pomodoro ahora", el bot agenda un bloque inmediato de 25 minutos y hace check-in al terminar.
- [ ] AC: Las respuestas del usuario a "¿qué te frena?" se guardan como `friction_notes` en la tarea para alimentar análisis futuros. (contribuye a: métrica "Tareas estancadas <20%")
- [ ] AC: El tono de la notificación se adapta al `communication_style` del perfil.

**Notas Técnicas:**
- Archivos: `ppai/push/application/friction_detector.py` (nuevo), `ppai/push/application/nudge_scheduler.py` (agregar `_evaluate_friction`), `ppai/capture/domain/entities.py` (campo `days_in_top3`, `friction_notes`)
- Modelo de datos: Extensión de `ppai-tasks` con `days_in_top3: int` y `friction_notes: list[str]`. Nuevo evento `FRICTION_DETECTED` en `ppai-events`.
- Servicios externos: Ninguno (V1 usa templates estáticos por estilo; V2 con LLM viene en ER4/HU-R4.3)
- Consideraciones: `days_in_top3` se incrementa cada vez que la tarea aparece en un Top 3 generado (en `DecisionService`). El friction detector evalúa una vez al día (en el plan matutino), no en cada tick.

---

### HU-R3.4 — Reporte semanal con insights accionables

**Como** usuario de PPAI
**Quiero** recibir cada domingo por la noche un reporte de mi semana con datos concretos (tareas completadas, patrones de procrastinación, día más/menos productivo) y sugerencias para la próxima semana
**Para** entender mis patrones de productividad y tomar decisiones informadas para mejorar

**Prioridad:** P1-crítico (DIFERENCIAL DEL PRODUCTO)
**UOW-R:** UOW-R3
**Dependencias:** ⚠️ Depende de: ER1/HU-R1.2 (perfil), ER2/HU-R2.2 (bloques para datos de completitud)

**Acceptance Criteria:**
- [ ] AC: Cada domingo a la hora configurada como `daily_end_time`, el bot envía un reporte semanal con: tareas completadas, tareas snoozed, tareas sin tocar, bloques completados vs planeados, día más productivo, y día menos productivo.
- [ ] AC: El reporte identifica al menos 1 patrón (ej: "Los jueves tienes 3 reuniones y no completas tareas" o "Las tareas personales las pospones siempre").
- [ ] AC: El reporte incluye 1-2 sugerencias concretas para la próxima semana basadas en los datos (ej: "Agenda solo tareas pequeñas los jueves").
- [ ] AC: El reporte cierra con una pregunta al usuario para ajustar el plan: "¿Quieres cambiar algo para la próxima semana?"
- [ ] AC: El reporte semanal solo se envía si el usuario tiene Google Calendar conectado (necesita datos de bloques para ser útil). Si no tiene Calendar, no se envía.
- [ ] AC: Si el usuario configuró `weekend_mode=rest`, el reporte se envía el lunes por la mañana en vez del domingo.
- [ ] AC: El tono del reporte se adapta al `communication_style` del perfil. (contribuye a: métrica "Tasa de snooze <30%")

**Notas Técnicas:**
- Archivos: `ppai/push/application/weekly_reporter.py` (nuevo), `ppai/push/application/nudge_scheduler.py` (agregar `_evaluate_weekly_insight`)
- Modelo de datos: Lectura agregada de `ppai-tasks` (completadas/snoozed en últimos 7 días), `ppai-time-blocks` (bloques completados vs planeados), `ppai-cycles` (nudge events por día).
- Servicios externos: Ninguno (V1 templates estáticos; V2 con LLM viene en ER4/HU-R4.4)
- Consideraciones: La query de datos semanales puede ser pesada (scan de 7 días de tareas + bloques). Usar GSI `userId-date-index` en time-blocks. Para tasks, filtrar por `updated_at` de los últimos 7 días. Considerar pre-calcular métricas al cierre de cada día y almacenar en un objeto `WeeklyMetrics`.

---

### HU-R3.5 — Check-in de medio día para días de baja actividad

**Como** usuario de PPAI
**Quiero** que si a medio día no he marcado ninguna tarea como completada, el bot me pregunte qué está pasando y me ofrezca reajustar el plan de la tarde
**Para** no perder el día completo cuando la mañana fue improductiva y recuperar el control de la tarde

**Prioridad:** P2-importante
**UOW-R:** UOW-R3
**Dependencias:** ⚠️ Depende de: ER2/HU-R2.2 (bloques), ER1/HU-R1.4 (tono)

**Acceptance Criteria:**
- [ ] AC: A la hora media entre `work_start` y `work_end`, si ningún bloque del día ha sido marcado como completado, el bot envía un check-in con 4 opciones: (1) mal día, las hago por la tarde, (2) surgieron cosas no planeadas, (3) necesito ayuda con alguna, (4) las voy a hacer ahora.
- [ ] AC: Si elige "surgieron cosas no planeadas", el bot pregunta qué pasó y ofrece capturar la actividad imprevista como tarea completada (para el registro).
- [ ] AC: Si elige opciones 1 o 2, el bot reajusta el plan de la tarde priorizando las tareas más urgentes y descartando las menos importantes.
- [ ] AC: El check-in NO se envía en días libres, festivos, ni fines de semana en modo descanso.
- [ ] AC: El check-in se envía máximo 1 vez al día (guard con evento `MIDDAY_CHECKIN_SENT`). (contribuye a: métrica "Días sin interacción <2/semana")

**Notas Técnicas:**
- Archivos: `ppai/push/application/nudge_scheduler.py` (agregar `_evaluate_midday_checkin`), `ppai/calendar/application/calendar_service.py` (reajuste de plan)
- Modelo de datos: Lectura de `ppai-time-blocks` (verificar si alguno tiene status `completed`). Nuevo evento `MIDDAY_CHECKIN_SENT`.
- Servicios externos: Ninguno
- Consideraciones: La hora media se calcula como `work_start + (work_end - work_start) / 2`. Para Angel con 9-18, sería las 13:30. Tolerancia de ±7min como los demás triggers del scheduler.

---

---

## ER4 — LLM como Cerebro del Asistente

> **UOW-R:** UOW-R4
> **Objetivo:** Integrar Claude (Anthropic API) en 4 puntos específicos donde el LLM aporta valor real: captura inteligente, mensajes con personalidad, análisis de fricción, y reportes semanales. Con fallback a templates estáticos si la API falla.
> **Estimación:** 12-14 steps de code generation

---

### HU-R4.1 — Captura inteligente de tareas con LLM

**Como** usuario de PPAI
**Quiero** que al capturar una tarea en texto libre, el bot use IA para clasificarla automáticamente con categoría, tiempo estimado y nivel de urgencia más precisos que las reglas actuales
**Para** que el planificador de bloques tenga información de mejor calidad y proponga planes más acertados

**Prioridad:** P2-importante
**UOW-R:** UOW-R4
**Dependencias:** ⚠️ Depende de: ER1/HU-R1.2 (perfil con ocupación para contexto del prompt)

**Acceptance Criteria:**
- [ ] AC: Al capturar una tarea, el LLM analiza el texto junto con la ocupación del usuario y devuelve: título normalizado, categoría, tiempo estimado en minutos, y nivel de urgencia.
- [ ] AC: La clasificación del LLM tiene una precisión perceptiblemente mejor que las reglas regex (categorización correcta en >80% de los casos vs ~50% con regex).
- [ ] AC: Si la API de Anthropic falla o tarda más de 5 segundos, el sistema usa automáticamente las reglas regex existentes como fallback, sin que el usuario note el cambio.
- [ ] AC: El costo de las llamadas al LLM para captura no supera $0.20/día (usando Claude Haiku).
- [ ] AC: La confirmación de captura muestra la categoría y estimación para que el usuario pueda corregir si es incorrecto.

**Notas Técnicas:**
- Archivos: `ppai/intelligence/infrastructure/anthropic_adapter.py` (nuevo), `ppai/intelligence/infrastructure/prompt_templates.py` (nuevo), `ppai/intelligence/domain/entities.py` (`TaskAnalysis`), `ppai/intelligence/application/task_analyzer.py` (nuevo), `ppai/capture/application/capture_service.py` (integración)
- Modelo de datos: `TaskAnalysis` value object con campos: `title`, `category`, `estimated_minutes`, `urgency`, `context`
- Servicios externos: Anthropic API (**Claude Haiku 4.5** para costo bajo — decisión confirmada). Env var: `ANTHROPIC_API_KEY`
- Consideraciones: Usar structured output (JSON) en el prompt. Timeout de 5s con fallback a regex. Cada llamada ~500 tokens input + 200 output = ~$0.0001 con Haiku. Para ~10 tareas/día = $0.001/día, muy dentro del presupuesto. Se eligió Haiku sobre Sonnet por relación costo/calidad suficiente para clasificación.

---

### HU-R4.2 — Mensajes con personalidad generados por LLM

**Como** usuario de PPAI
**Quiero** que los mensajes del bot (inicio de día, cierre, nudges) se generen dinámicamente con IA para que sean contextuales, empáticos y adaptados a mi situación del día
**Para** sentir que el bot realmente me entiende y no me envía templates genéricos repetitivos

**Prioridad:** P2-importante
**UOW-R:** UOW-R4
**Dependencias:** ⚠️ Depende de: ER1/HU-R1.4 (templates estáticos como fallback), ER2/HU-R2.2 (datos de bloques para contexto)

**Acceptance Criteria:**
- [ ] AC: El mensaje de inicio de día se genera con LLM incluyendo: nombre del usuario, plan de bloques, contexto de tareas atascadas, y datos del día anterior.
- [ ] AC: El mensaje de cierre de día se genera con LLM incluyendo: resumen de completitud, datos de bloques completados vs planeados, y sugerencia para mañana.
- [ ] AC: El LLM respeta las frases prohibidas (`debías`, `ya vas tarde`, `otra vez`) independientemente del estilo de comunicación.
- [ ] AC: Si la API falla, los mensajes se generan con los templates estáticos de HU-R1.4 sin que el usuario pierda funcionalidad.
- [ ] AC: Los mensajes generados no superan 150 palabras para mantener la concisión.
- [ ] AC: El costo de mensajes LLM no supera $0.05/día (1 matutino + 1 cierre + ~5 nudges). (contribuye a: métrica "¿Siento que PPAI me conoce?")

**Notas Técnicas:**
- Archivos: `ppai/intelligence/application/message_composer.py` (nuevo), `ppai/push/application/nudge_service.py` (integración), `ppai/push/application/daily_summary_builder.py` (integración)
- Modelo de datos: `MessageRequest` entity con campos: `user_profile`, `top3_tasks`, `day_plan`, `yesterday_stats`, `communication_style`
- Servicios externos: Anthropic API (Claude Haiku para nudges, Claude Sonnet para mensajes matutinos/cierre)
- Consideraciones: Usar system prompt con reglas de tono y frases prohibidas. Incluir `communication_style` en el prompt. Retry 1 vez con timeout 8s, luego fallback a template. El MessageComposer debe ser un servicio inyectable para facilitar testing con mocks.

---

### HU-R4.3 — Análisis inteligente de fricción con estrategias personalizadas

**Como** usuario de PPAI que tiene una tarea estancada
**Quiero** que el bot analice mi historial con esa tarea y me dé un diagnóstico probable de por qué la procrastino junto con estrategias concretas personalizadas
**Para** entender mi patrón de bloqueo y recibir ayuda accionable para destrabar la tarea

**Prioridad:** P1-crítico (DIFERENCIAL DEL PRODUCTO)
**UOW-R:** UOW-R4
**Dependencias:** ⚠️ Depende de: ER3/HU-R3.3 (friction detector que dispara el análisis)

**Acceptance Criteria:**
- [ ] AC: Cuando el friction detector identifica una tarea estancada (3+ días), el LLM recibe el historial completo de la tarea (días en Top 3, snoozes, friction_notes previas) y genera: diagnóstico probable, 3 estrategias concretas, y 1 micro-acción de máximo 15 minutos.
- [ ] AC: Las estrategias son específicas al contexto del usuario (ocupación, tipo de tarea) y no genéricas (no "divide la tarea en partes", sino "dedica 15 min a leer solo la documentación del endpoint").
- [ ] AC: Si el usuario ha respondido "¿qué te frena?" previamente, esas notas se incluyen en el prompt para dar continuidad al análisis.
- [ ] AC: Si la API falla, el friction detector usa las opciones estáticas definidas en HU-R3.3 como fallback.
- [ ] AC: El análisis se genera máximo 1 vez por tarea por día (no spam). (contribuye a: métrica "Tareas estancadas <20%")

**Notas Técnicas:**
- Archivos: `ppai/intelligence/application/friction_analyzer.py` (nuevo), `ppai/push/application/friction_detector.py` (integración con LLM)
- Modelo de datos: Lectura de `TaskState.days_in_top3`, `TaskState.snooze_count`, `TaskState.friction_notes`, `UserProfile.occupation`, `UserProfile.communication_style`
- Servicios externos: Anthropic API (Claude Sonnet recomendado para calidad de análisis — este es el feature diferencial)
- Consideraciones: Este es el punto donde el LLM más valor agrega. Usar Sonnet en vez de Haiku para calidad. El costo extra (~$0.03/análisis, ~2/día = $0.06) está justificado por ser el diferencial del producto. Incluir friction_notes anteriores en el prompt para que el LLM no repita sugerencias.

---

### HU-R4.4 — Reporte semanal enriquecido con insights de LLM

**Como** usuario de PPAI
**Quiero** que mi reporte semanal sea analizado por IA para identificar patrones de productividad y procrastinación que yo no vería en los datos crudos
**Para** recibir insights accionables y personalizados que me ayuden a mejorar semana a semana

**Prioridad:** P1-crítico (DIFERENCIAL DEL PRODUCTO)
**UOW-R:** UOW-R4
**Dependencias:** ⚠️ Depende de: ER3/HU-R3.4 (weekly reporter con datos crudos)

**Acceptance Criteria:**
- [ ] AC: El LLM recibe los datos agregados de la semana (tareas completadas/snoozed/sin tocar, bloques completados vs planeados, distribución por categoría, día más/menos productivo) y genera un reporte con: qué salió bien, 1 patrón problemático, 1 sugerencia concreta, y 1 pregunta al usuario.
- [ ] AC: Los insights del LLM son específicos a los datos ("Los jueves completaste 0 tareas porque tuviste 3h de reuniones") y no genéricos ("Intenta ser más productivo").
- [ ] AC: El reporte compara con la semana anterior si hay datos disponibles (ej: "Completaste 12 tareas vs 8 la semana pasada, +50%").
- [ ] AC: Si la API falla, se envía el reporte con datos crudos y sin análisis (como en HU-R3.4).
- [ ] AC: El costo del weekly insight no supera $0.02/semana (1 llamada con Sonnet). (contribuye a: métrica "¿Uso PPAI todos los días laborales?")

**Notas Técnicas:**
- Archivos: `ppai/intelligence/application/weekly_reporter.py` (nuevo), `ppai/push/application/weekly_reporter.py` (integración con LLM)
- Modelo de datos: `WeeklyReport` entity con métricas agregadas. Lectura de datos de `ppai-tasks`, `ppai-time-blocks`, `ppai-cycles`.
- Servicios externos: Anthropic API (Claude Sonnet para calidad de insights)
- Consideraciones: Una sola llamada al LLM por semana — costo despreciable ($0.02). Usar Sonnet para máxima calidad. Incluir datos de la semana anterior si existen para comparación. El prompt debe pedir máximo 200 palabras para mantener concisión.

---

---

## ER5 — Captura con Asignación Directa a Calendar

> **UOW-R:** UOW-R5
> **Objetivo:** Que cuando el usuario capture una tarea con duración explícita o horario definido, PPAI la agende directamente en Google Calendar sin requerir `/plan`. Reduce la fricción del loop captura → agenda a un solo mensaje.
> **Estimación:** 10-12 steps de code generation
> **Nota (Decisión Angel):** Dos variantes soportadas: (1) horario explícito via hashtag `#15:00-15:30` → crea directo, (2) solo duración `1 hora` → el sistema sugiere horario. Respetar ventana de silencio y horario laboral.

---

### HU-R5.1 — Detección de duración y horario en texto de captura

**Como** usuario de PPAI
**Quiero** que al capturar una tarea pueda incluir duración ("30min", "1h", "45 minutos") o un horario explícito ("#15:00-15:30") en el mismo mensaje
**Para** que PPAI entienda cuánto tiempo necesito y cuándo quiero hacerla sin un paso adicional

**Prioridad:** P1-crítico
**UOW-R:** UOW-R5
**Dependencias:** E1/S1.1 (captura base existente)

**Acceptance Criteria:**
- [ ] AC: El parser de captura detecta duraciones en formatos: `30min`, `30 min`, `1h`, `1 hora`, `1.5h`, `45 minutos`, `2 horas` y los almacena como `estimated_minutes` en la tarea.
- [ ] AC: El parser detecta horarios explícitos en formato hashtag: `#15:00-15:30`, `#9:00-10:00`, `#14:30-16:00` y los almacena como `requested_slot` (start, end) en la tarea.
- [ ] AC: La duración y el horario se extraen del texto sin afectar el título normalizado de la tarea (ej: "Practicar guitarra 30min #hobby" → título: "Practicar guitarra", duración: 30min, categoría: hobby).
- [ ] AC: Si el usuario especifica tanto duración como horario explícito, el horario explícito tiene prioridad y la duración se ignora.
- [ ] AC: Si no se detecta duración ni horario, la captura funciona exactamente como antes (sin cambios al flujo actual).

**Notas Técnicas:**
- Archivos: `ppai/capture/domain/value_objects.py` (nuevo `TimeSlot`, `Duration`), `ppai/capture/application/capture_service.py` (extender parser), `ppai/capture/domain/entities.py` (campos `estimated_minutes`, `requested_slot`)
- Modelo de datos: Extensión de `ppai-tasks` con `estimated_minutes: int | None` y `requested_slot: {start: str, end: str} | None`
- Servicios externos: Ninguno
- Consideraciones: Usar regex para V1. Si ER4/HU-R4.1 (captura LLM) ya está implementado, la extracción de duración/horario se delega al LLM en vez de regex. El regex es el fallback.

---

### HU-R5.2 — Asignación automática a Calendar con horario explícito

**Como** usuario de PPAI con calendario conectado
**Quiero** que si capturo una tarea con horario explícito (ej: "Reunión con diseñador #14:00-15:00 #trabajo"), PPAI cree el evento directamente en mi Google Calendar
**Para** agendar y capturar en un solo mensaje sin pasar por `/plan`

**Prioridad:** P1-crítico
**UOW-R:** UOW-R5
**Dependencias:** ER2/HU-R2.1 (Calendar conectado), HU-R5.1

**Acceptance Criteria:**
- [ ] AC: Si la tarea tiene `requested_slot` y el usuario tiene Calendar conectado, PPAI crea automáticamente un evento `[PPAI] <título>` en Google Calendar en el slot indicado.
- [ ] AC: Si el horario solicitado ya pasó (ej: son las 16:00 y pide #14:00-15:00), el bot informa y ofrece dos opciones: (1) agendar hoy en el próximo hueco libre, (2) agendar mañana en el mismo horario.
- [ ] AC: Si el horario solicitado cae dentro de la ventana de silencio del usuario, el bot informa y sugiere agendarlo para el día siguiente respetando el horario pedido.
- [ ] AC: Si el horario solicitado se solapa con un evento existente en Calendar, el bot informa del conflicto y sugiere el hueco libre más cercano.
- [ ] AC: El bot confirma la creación: "✅ Capturado y agendado de 14:00 a 15:00 en tu calendario."
- [ ] AC: Si el usuario no tiene Calendar conectado, la tarea se captura normalmente sin agendar y se sugiere conectar con `/calendar`.

**Notas Técnicas:**
- Archivos: `ppai/capture/application/capture_service.py` (orquestar flujo), `ppai/calendar/application/calendar_service.py` (crear evento, verificar conflictos), `ppai/calendar/application/block_planner.py` (reutilizar lógica de huecos libres)
- Modelo de datos: Reutiliza `TimeBlock` existente de ER2. El evento creado se registra en `ppai-time-blocks`.
- Servicios externos: Google Calendar API (write)
- Consideraciones: Reutilizar `BlockPlanner.find_free_slots()` y `CalendarService.create_event()` de ER2. La lógica de conflicto/sugerencia es nueva pero se apoya en las consultas existentes. El flujo de confirmación usa botones inline [Hoy otro horario] [Mañana] cuando hay conflicto.

---

### HU-R5.3 — Sugerencia de horario al capturar tarea con duración

**Como** usuario de PPAI con calendario conectado
**Quiero** que si capturo una tarea con duración pero sin horario específico (ej: "Practicar guitarra 1 hora #hobby"), PPAI me sugiera el próximo hueco libre para agendarla
**Para** decidir rápidamente cuándo hacerla sin tener que revisar mi calendario manualmente

**Prioridad:** P1-crítico
**UOW-R:** UOW-R5
**Dependencias:** ER2/HU-R2.2 (BlockPlanner), HU-R5.1

**Acceptance Criteria:**
- [ ] AC: Si la tarea tiene `estimated_minutes` (sin `requested_slot`) y el usuario tiene Calendar conectado, el bot busca el próximo hueco libre que quepa la duración, respetando horario laboral y bloques protegidos.
- [ ] AC: El bot sugiere el horario con botones inline: "📅 Agendar de 15:00 a 16:00? [Sí] [Cambiar hora] [No agendar]".
- [ ] AC: Si el usuario presiona [Sí], se crea el evento `[PPAI]` en Calendar y se confirma.
- [ ] AC: Si presiona [Cambiar hora], el bot pide un horario alternativo y valida disponibilidad antes de crear.
- [ ] AC: Si presiona [No agendar], la tarea queda capturada normalmente sin evento en Calendar.
- [ ] AC: Si no hay huecos disponibles hoy (agenda llena), el bot sugiere el primer hueco de mañana.
- [ ] AC: Si la hora actual + duración excede la hora de fin de jornada, el bot sugiere mañana directamente.

**Notas Técnicas:**
- Archivos: `ppai/capture/application/capture_service.py` (orquestar sugerencia), `ppai/calendar/application/block_planner.py` (buscar hueco), `ppai/bot/callbacks/schedule_callbacks.py` (nuevo — manejar botones inline de sugerencia)
- Modelo de datos: Reutiliza `BlockPlanner` de ER2 para búsqueda de huecos. Nuevo callback data pattern: `schedule_yes:<task_id>:<slot>`, `schedule_change:<task_id>`, `schedule_no:<task_id>`.
- Servicios externos: Google Calendar API (read + write)
- Consideraciones: El flujo de sugerencia es asíncrono (espera respuesta del usuario via callback). Si el usuario no responde, la tarea queda sin agendar (sin timeout ni recordatorio adicional). La búsqueda de huecos prioriza: (1) hoy si quedan horas, (2) mañana si no. No buscar más allá de mañana para mantener simplicidad.

---

---

## Resumen de prioridades

| Prioridad | HUs | Descripción |
|-----------|-----|-------------|
| P1-crítico | HU-R1.1, HU-R1.2, HU-R1.4, HU-R1.5, HU-R2.1, HU-R2.2, HU-R2.4, HU-R3.1, HU-R3.3, HU-R3.4, HU-R4.3, HU-R4.4, HU-R5.1, HU-R5.2, HU-R5.3 | Core del refactor + diferenciales (anti-fricción, reportes, personalización, captura→calendar) |
| P2-importante | HU-R1.3, HU-R2.3, HU-R2.5, HU-R3.5, HU-R4.1, HU-R4.2 | Necesario pero no diferencial (festivos, escritura en Calendar, LLM para captura/mensajes) |
| P3-deseable | HU-R3.2 | Nice-to-have (detector de huecos por cambios en Calendar) |

---

## Lo que NO se incluye en este backlog

Extraído de la sección 13 del REFACTOR_PLAN.md:

1. Dashboard web
2. Login con Google para perfil
3. Integración con Slack/email
4. Bloqueo de apps
5. Subtareas (el friction analyzer sugiere dividir manualmente)
6. Multi-calendario (solo Google Calendar personal)
7. Exportar datos
8. Teams/sharing
9. Migración a CLI
10. ML custom (solo Claude API)

---

## Preguntas resueltas

> Todas las preguntas abiertas fueron respondidas por Angel el 2026-03-27.

| # | HU | Pregunta | Decisión |
|---|-----|----------|----------|
| 1 | HU-R2.1 | ¿Cómo manejar el Google Cloud Project para OAuth? | **A) Crear proyecto dedicado "PPAI"** en Google Cloud |
| 2 | HU-R2.1 | ¿Los tokens OAuth se encriptan con AWS KMS o clave local? | **B) Fernet con clave en env var** (más simple) |
| 3 | HU-R2.4 | ¿Permitir categoría manual al capturar? | **C) Ambos** — hashtag como override + corrección post-captura |
| 4 | HU-R1.3 | ¿Qué pasa si `holidays` no soporta el país? | **C) Usar festivos de Colombia como default** |
| 5 | HU-R3.4 | ¿Reporte semanal sin Calendar conectado? | **B) No enviar reporte** hasta que Calendar esté conectado |
| 6 | HU-R4.1 | ¿Haiku o Sonnet para captura inteligente? | **A) Haiku** (suficiente para clasificación, más barato) |
| 7 | HU-R3.3 | ¿Cuántos días disparan friction detector? | **A) 3 días** (como está propuesto) |
