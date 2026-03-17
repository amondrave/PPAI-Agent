# Business Logic Model — UOW-01 Capture Foundation

## Overview
Este modelo describe el flujo de negocio desde la recepcion de un mensaje Telegram hasta la persistencia de tareas normalizadas y emision de evento minimo.

## Flow: Capture Intent

```
Telegram Message
      |
      v
[1. Validate Input]
      |
      +-- INVALID --> [Return reformulation request] --> END
      |
      v
[2. Parse Lines (multi-task)]
      |
      v
[3. For each line:]
      |
      +---> [3a. Normalize]
      |         |
      |         v
      +---> [3b. Extract tag/deadline]
      |         |
      |         v
      +---> [3c. Check dedup]
      |         |
      |         +-- DUPLICATE --> [Skip, log] --> continue
      |         |
      |         v
      +---> [3d. Check active task limit]
      |         |
      |         +-- LIMIT REACHED --> [Reject with message] --> END
      |         |
      |         v
      +---> [3e. Create TaskState (status=captured)]
      |         |
      |         v
      +---> [3f. Transition to pending]
      |         |
      |         v
      +---> [3g. Persist TaskState]
      |         |
      |         v
      +---> [3h. Emit CaptureEvent (best effort)]
      |         |
      |         v
      +---> [3i. Record DedupRecord]
      |
      v
[4. Send confirmation message]
      |
      v
END
```

## Step Details

### Step 1: Validate Input
- **Input**: TelegramUpdate (message object)
- **Logic**:
  1. Rechazar si el mensaje no contiene texto (stickers, fotos, media sin caption) -> responder pidiendo texto
  2. Rechazar si el texto es vacio o solo whitespace/emojis sin caracteres alfanumericos -> responder pidiendo reformulacion
  3. Si es texto valido, continuar al paso 2
- **Output**: Texto crudo validado o mensaje de error al usuario

### Step 2: Parse Lines (Multi-Task)
- **Input**: Texto crudo validado
- **Logic**:
  1. Dividir el texto por saltos de linea (`\n`)
  2. Filtrar lineas vacias o solo whitespace
  3. Cada linea no-vacia es una intencion independiente
- **Output**: Lista de strings (una por tarea potencial)

### Step 3a: Normalize
- **Input**: Linea de texto cruda
- **Logic**:
  1. Trim whitespace
  2. Preservar texto original en campo `originalText`
  3. Generar `normalizedText`: trim + colapsar espacios multiples
- **Output**: Par (originalText, normalizedText)

### Step 3b: Extract Tag/Deadline
- **Input**: normalizedText
- **Logic**:
  1. **Tag**: Buscar patron `#palabra` en el texto. Si existe, extraer como `tag` y remover del normalizedText
  2. **Deadline**: Buscar patrones temporales simples en espanol:
     - "para manana" / "manana" -> dia siguiente 09:00
     - "para hoy" / "hoy" -> hoy 23:59
     - "urgente" -> hoy 23:59 + flag urgente
     - Formato explicito: "para DD/MM" o "para YYYY-MM-DD"
  3. Si no se detecta patron, tag=null y deadline=null
- **Output**: (cleanedText, tag | null, deadline | null)

### Step 3c: Check Dedup
- **Input**: userId, exactText (texto exacto original del usuario)
- **Logic**:
  1. Buscar en DedupRecord: mismo userId + mismo exactText + lastSeenAt dentro de ultimos 5 minutos
  2. Si existe match -> marcar como duplicado, skip
  3. Si no existe match -> continuar
- **Output**: Boolean (isDuplicate)

### Step 3d: Check Active Task Limit
- **Input**: userId
- **Logic**:
  1. Contar tareas activas del usuario (estados: captured, pending, prioritized, nudged, snoozed, clarifying)
  2. Si count >= ACTIVE_TASK_LIMIT (configurable, default 50) -> rechazar
- **Output**: Boolean (limitReached)

### Step 3e-3f: Create and Transition TaskState
- **Input**: Datos normalizados
- **Logic**:
  1. Crear TaskState con status=`captured`, todos los campos poblados
  2. Transicionar inmediatamente a status=`pending` (tarea lista para priorizacion)
  3. updatedAt refleja el momento de la transicion
- **Output**: TaskState persistible

### Step 3g: Persist TaskState
- **Input**: TaskState completa
- **Logic**: Upsert en Loop State Store via TaskStateRepository
- **Output**: SaveResult

### Step 3h: Emit CaptureEvent
- **Input**: TaskState creada
- **Logic**:
  1. Construir CaptureEvent con eventType=`INTENT_CAPTURED`
  2. Persistir via EventRepository (best effort)
  3. Si falla la escritura del evento, loggear error pero NO fallar la captura
- **Output**: AppendResult (best effort)

### Step 3i: Record DedupRecord
- **Input**: userId, exactText, taskId
- **Logic**: Insertar/actualizar DedupRecord con TTL de 5 minutos
- **Output**: void

### Step 4: Send Confirmation
- **Input**: Lista de tareas creadas exitosamente
- **Logic**:
  1. Si se creo 1 tarea: "Capturado. Tu tarea ha sido registrada."
  2. Si se crearon N tareas: "Capturado. N tareas han sido registradas."
  3. Si algunas fueron duplicadas: "Capturado. N tareas registradas. M duplicadas omitidas."
  4. Si se alcanzo el limite: "Limite de tareas activas alcanzado (LIMIT). Completa o elimina tareas existentes para agregar nuevas."
- **Output**: Mensaje de confirmacion enviado via Telegram Adapter

## Error Handling

| Scenario | Behavior |
|---|---|
| Telegram API timeout al enviar confirmacion | Loggear error, no reintentar (usuario puede reenviar) |
| Fallo de persistencia de TaskState | Retornar error al usuario, no emitir evento |
| Fallo de persistencia de CaptureEvent | Loggear warning, captura ya exitosa (best effort) |
| Fallo de DedupRecord write | Loggear warning, captura exitosa (peor caso: duplicado futuro pasa) |

## Constants

| Name | Default Value | Description |
|---|---|---|
| ACTIVE_TASK_LIMIT | 50 | Maximo de tareas activas por usuario |
| DEDUP_WINDOW_SECONDS | 300 | Ventana de deduplicacion (5 minutos) |
| SUPPORTED_DEADLINE_PATTERNS | ver Step 3b | Patrones de deadline reconocidos |
