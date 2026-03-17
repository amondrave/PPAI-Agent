# Functional Design Plan — UOW-01 Capture Foundation

## Unit Context
- **Unit**: UOW-01 Capture Foundation
- **Goal**: Habilitar captura robusta de intencion por Telegram.
- **Stories**: US-01 (Capture de intencion en lenguaje natural), US-02 (Normalizacion minima de captura)
- **Components**: C1 (Telegram Adapter), C2 (Capture & Normalization), C8 (Loop State Store), C9 (Event Log)

## Plan Steps

- [x] 1. Definir entidad de dominio `Intent` (campos, estados, ciclo de vida)
- [x] 2. Definir entidad de dominio `TaskState` (campos iniciales, estados validos)
- [x] 3. Disenar flujo de negocio: mensaje Telegram -> validacion -> normalizacion -> persistencia -> evento
- [x] 4. Documentar reglas de negocio de validacion de entrada (mensajes vacios, no interpretables)
- [x] 5. Documentar reglas de negocio de normalizacion (que se extrae, que se preserva)
- [x] 6. Documentar reglas de negocio de deduplicacion por ventana temporal
- [x] 7. Documentar reglas de negocio de confirmacion de recepcion al usuario
- [x] 8. Documentar reglas de negocio de capturas multiples en sesion
- [x] 9. Definir contrato de evento minimo de captura
- [x] 10. Validar cobertura de acceptance criteria de US-01 y US-02

## Clarification Questions

### Q1. Modelo de Intencion/Tarea
Al capturar una intencion, el texto libre del usuario se convierte en una entidad interna. Que campos adicionales al texto original necesitas en la entidad de tarea?

A) Solo lo minimo: ID, texto original, timestamp, estado, userId
B) Agregar campo de categoria/etiqueta opcional que el usuario pueda poner con hashtag (ej: #trabajo)
C) Agregar campo de urgencia/deadline opcional que el usuario pueda expresar en el texto
D) B + C combinados (etiqueta + urgencia)
E) Otro (especificar en respuesta)

[Answer]: D

### Q2. Validacion de Mensajes No Interpretables
US-01 dice "si el mensaje esta vacio/no interpretable, solicita reformulacion". Que consideras "no interpretable" para MVP?

A) Solo mensajes vacios o solo whitespace/emojis sin texto
B) Mensajes demasiado cortos (menos de N caracteres, ej: menos de 3)
C) Mensajes que son solo stickers, fotos o media sin texto (no soportar media en MVP)
D) A + C (vacios + media sin texto)

[Answer]: D

### Q3. Ventana de Deduplicacion
US-02 menciona "mensajes duplicados cercanos en tiempo se marcan para deduplicacion simple". Que estrategia prefieres?

A) Deduplicacion por texto exacto dentro de ventana de 60 segundos
B) Deduplicacion por texto exacto dentro de ventana de 5 minutos
C) Deduplicacion por similitud basica (lowercase + trim) dentro de ventana de 60 segundos
D) Deduplicacion por similitud basica dentro de ventana de 5 minutos

[Answer]: B

### Q4. Confirmacion de Recepcion
US-01 dice "confirma recepcion". Como quieres la confirmacion?

A) Mensaje de texto simple fijo (ej: "Capturado. Tu tarea ha sido registrada.")
B) Mensaje con eco del texto capturado (ej: "Capturado: [texto normalizado]")
C) Mensaje con eco + numero de tareas activas del usuario (ej: "Capturado: [texto]. Tienes 5 tareas activas.")

[Answer]: A

### Q5. Capturas Multiples en Sesion
US-01 dice "soporta multiples capturas en una misma sesion conversacional". Esto significa:

A) Cada mensaje individual del usuario es una captura separada (1 mensaje = 1 tarea)
B) El usuario puede enviar multiples tareas en un solo mensaje separadas por salto de linea
C) Ambas (cada mensaje es una tarea, y si un mensaje tiene multiples lineas, cada linea es una tarea)

[Answer]: B

### Q6. Estado Inicial de Tarea
Al crear una tarea por captura, cual es el estado inicial en el ciclo de vida?

A) `captured` (indicando que fue capturada pero aun no priorizada)
B) `pending` (indicando que esta lista para priorizacion)
C) `inbox` (indicando que esta en bandeja de entrada sin procesar)

[Answer]: A

### Q7. Evento Minimo de Captura
El evento minimo que se registra al capturar. Que nivel de detalle?

A) Solo tipo de evento + taskId + timestamp + userId
B) A + texto original capturado
C) A + texto normalizado (sin texto original por sensibilidad)
D) A + ambos textos (original y normalizado)

[Answer]:B

### Q8. Limite de Tareas Activas
Debe haber un limite de tareas activas por usuario en MVP?

A) No, sin limite
B) Si, con limite suave (warning al superar N tareas, ej: 25)
C) Si, con limite duro (rechazar captura al superar N tareas)

[Answer]:C
