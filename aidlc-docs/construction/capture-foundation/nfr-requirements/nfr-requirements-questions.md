# NFR Requirements — Preguntas de Clarificación — UOW-01 Capture Foundation

Por favor responde cada pregunta con la letra de la opción elegida después del tag `[Answer]:`.

---

## Question 1
¿Cuántos usuarios concurrentes esperas en el MVP de PPAI?

A) Uso personal (1-5 usuarios, solo tú y personas cercanas)
B) Beta cerrada (10-50 usuarios invitados)
C) Beta abierta (50-500 usuarios)
D) Producción a escala (500+ usuarios)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
¿Cuál es la latencia máxima aceptable para la confirmación de captura en Telegram (desde que el usuario envía el mensaje hasta que recibe "Capturado")?

A) Menos de 1 segundo (experiencia instantánea)
B) 1-3 segundos (rápida, aceptable para bot)
C) 3-5 segundos (tolerable para MVP)
D) No es crítico mientras funcione (sin SLO estricto para MVP)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 3
¿Qué nivel de disponibilidad necesitas para el bot Telegram en MVP?

A) Best effort — si se cae, lo reinicio manualmente, aceptable para uso personal
B) Razonable — debería estar arriba la mayor parte del tiempo, con restart automático si falla
C) Alta disponibilidad — el bot no debería caerse, necesito que las capturas nunca se pierdan
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 4
¿Qué lenguaje/runtime prefieres para la implementación del backend?

A) TypeScript con Node.js
B) Python
C) Go
D) Kotlin/JVM
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 5
¿Qué base de datos prefieres para el estado materializado (TaskState, DedupRecord)?

A) PostgreSQL (relacional, robusto, bien soportado)
B) SQLite (simple, sin servidor, ideal para MVP personal)
C) DynamoDB (serverless, escalable, key-value/document)
D) MongoDB (document store, flexible schema)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 6
¿Dónde planeas desplegar el MVP?

A) Máquina local o VPS simple (ej: DigitalOcean, Linode, EC2 single instance)
B) Contenedor en servicio managed (ej: AWS ECS/Fargate, Google Cloud Run, Azure Container Apps)
C) Serverless functions (ej: AWS Lambda, Google Cloud Functions)
D) Kubernetes (EKS, GKE, self-managed)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 7
¿Cómo quieres manejar la autenticación del bot y la autorización de usuarios?

A) Solo el bot token de Telegram, sin autenticación adicional — cualquier usuario que hable con el bot puede usarlo
B) Whitelist de Telegram user IDs — solo usuarios autorizados pueden interactuar
C) Registro abierto al primer mensaje, pero cada usuario opera en su propio espacio aislado
D) B + C combinados (whitelist + aislamiento por usuario)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 8
¿Qué estrategia de rate limiting prefieres para proteger el bot contra abuso?

A) Sin rate limiting en MVP (confío en la whitelist o uso personal)
B) Rate limit simple: máximo N mensajes por usuario por minuto (ej: 10/min)
C) Rate limit por niveles: suave (warning) + duro (bloqueo temporal)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 9
¿Qué nivel de logging y observabilidad necesitas para el MVP?

A) Mínimo — logs a stdout/stderr, consulto manualmente si hay problemas
B) Estructurado — JSON logs con correlación, exportados a un servicio (ej: CloudWatch, Datadog)
C) Completo — logs estructurados + métricas de negocio (capturas/min, errores) + alertas básicas
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 10
¿Cómo prefieres manejar los secretos (bot token, credenciales de DB)?

A) Variables de entorno en el host/contenedor (simple, sin servicio externo)
B) Archivo `.env` local (solo desarrollo) + variables de entorno en producción
C) Secrets manager dedicado (ej: AWS Secrets Manager, HashiCorp Vault)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 11
¿Qué estrategia de testing quieres para UOW-01?

A) Tests unitarios para lógica de negocio (normalización, dedup, validación)
B) A + tests de integración (flujo completo con DB real)
C) A + B + tests e2e contra API de Telegram (con mock del API)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 12
Para el evento mínimo de captura (CaptureEvent), ¿dónde quieres persistirlo?

A) En la misma base de datos que TaskState (tabla/colección separada)
B) En un archivo append-only local (JSONL/log file)
C) En un servicio de eventos dedicado (ej: EventBridge, Kafka, SQS)
X) Other (please describe after [Answer]: tag below)

[Answer]: A
