# Business Rules — UOW-01 Capture Foundation

## BR-CAP-01: Input Validation
- **Rule**: Solo se aceptan mensajes de texto. Media sin texto (stickers, fotos, audio, video, documentos sin caption) se rechazan con solicitud de reformulacion.
- **Trigger**: Recepcion de TelegramUpdate
- **Condition**: message.text es null o vacio o solo whitespace/emojis sin alfanumericos
- **Action**: Responder "No pude interpretar tu mensaje. Por favor envia tu tarea como texto."
- **Priority**: Blocking (no continua flujo)

## BR-CAP-02: Multi-Line Parsing
- **Rule**: Un mensaje con multiples lineas genera multiples tareas independientes.
- **Trigger**: Texto validado con saltos de linea
- **Condition**: Texto contiene `\n` y al menos 2 lineas no-vacias
- **Action**: Cada linea no-vacia se procesa como intencion independiente
- **Constraint**: Lineas vacias o solo whitespace se ignoran silenciosamente

## BR-CAP-03: Tag Extraction
- **Rule**: Hashtags en el texto se extraen como etiqueta de tarea.
- **Trigger**: Normalizacion de texto
- **Condition**: Texto contiene patron `#palabra` (alfanumerico, sin espacios)
- **Action**: Extraer primer hashtag como `tag`, remover del normalizedText
- **Constraint**: Solo se extrae el primer hashtag encontrado. Hashtags adicionales permanecen en el texto.

## BR-CAP-04: Deadline Extraction
- **Rule**: Expresiones temporales simples se extraen como deadline.
- **Trigger**: Normalizacion de texto
- **Condition**: Texto contiene patron temporal reconocido
- **Patterns reconocidos**:
  - "para manana" / "manana" -> dia siguiente 09:00 local
  - "para hoy" / "hoy" -> mismo dia 23:59 local
  - "urgente" -> mismo dia 23:59 local (flag implicito)
  - "para DD/MM" -> fecha especifica 09:00 local
  - "para YYYY-MM-DD" -> fecha especifica 09:00 local
- **Action**: Extraer deadline como DateTime, remover expresion temporal del normalizedText
- **Constraint**: Si no se detecta patron, deadline=null. No forzar deadline.

## BR-CAP-05: Deduplication
- **Rule**: Mensajes con texto exacto identico del mismo usuario dentro de ventana de 5 minutos se consideran duplicados.
- **Trigger**: Post-normalizacion, pre-persistencia
- **Condition**: Existe DedupRecord con mismo (userId, exactText) donde lastSeenAt < 5 minutos atras
- **Action**: Omitir creacion de tarea para esa linea. Contabilizar como "duplicada omitida" en confirmacion.
- **Comparison**: Texto exacto (case-sensitive, sin transformaciones)

## BR-CAP-06: Active Task Limit
- **Rule**: Existe un limite duro de tareas activas por usuario.
- **Trigger**: Pre-persistencia de nueva tarea
- **Condition**: Count de tareas activas del usuario >= ACTIVE_TASK_LIMIT (default: 50)
- **Action**: Rechazar captura con mensaje: "Limite de tareas activas alcanzado (50). Completa o elimina tareas existentes para agregar nuevas."
- **Active states**: captured, pending, prioritized, nudged, snoozed, clarifying
- **Constraint**: El limite aplica por usuario, no global. Tareas en estado `done` no cuentan.

## BR-CAP-07: Confirmation Response
- **Rule**: Toda captura exitosa recibe confirmacion fija.
- **Trigger**: Post-persistencia exitosa
- **Messages**:
  - 1 tarea: "Capturado. Tu tarea ha sido registrada."
  - N tareas: "Capturado. N tareas han sido registradas."
  - Con duplicados: "Capturado. N tareas registradas. M duplicadas omitidas."
  - Limite alcanzado (mid-batch): "Capturado. N tareas registradas. Limite alcanzado, M tareas no pudieron agregarse."

## BR-CAP-08: Event Emission (Best Effort)
- **Rule**: Cada tarea creada emite un evento INTENT_CAPTURED.
- **Trigger**: Post-persistencia exitosa de TaskState
- **Action**: Escribir CaptureEvent via EventRepository
- **Constraint**: Best effort. Si falla la escritura, loggear warning pero la captura se considera exitosa.
- **Rationale**: La fuente de verdad es el estado materializado (TaskState), no el event log.

## BR-CAP-09: Original Text Preservation
- **Rule**: El texto original del usuario siempre se preserva intacto.
- **Trigger**: Normalizacion
- **Action**: Almacenar `originalText` sin modificaciones en TaskState
- **Constraint**: La normalizacion solo afecta `normalizedText`. El campo `originalText` es inmutable post-creacion.

## BR-CAP-10: State Lifecycle Entry
- **Rule**: Toda tarea nueva entra en estado `captured` y transiciona inmediatamente a `pending`.
- **Trigger**: Creacion de TaskState
- **Sequence**: captured (instantaneo) -> pending
- **Constraint**: No debe existir tarea que permanezca en estado `captured` mas alla del flujo de creacion.

## Rules Summary Table

| Rule ID | Name | Type | Blocking |
|---|---|---|---|
| BR-CAP-01 | Input Validation | Validation | Yes |
| BR-CAP-02 | Multi-Line Parsing | Transformation | No |
| BR-CAP-03 | Tag Extraction | Extraction | No |
| BR-CAP-04 | Deadline Extraction | Extraction | No |
| BR-CAP-05 | Deduplication | Guard | Per-line |
| BR-CAP-06 | Active Task Limit | Guard | Yes |
| BR-CAP-07 | Confirmation Response | Output | No |
| BR-CAP-08 | Event Emission | Side-effect | No (best effort) |
| BR-CAP-09 | Original Text Preservation | Invariant | Yes |
| BR-CAP-10 | State Lifecycle Entry | Transition | Yes |
