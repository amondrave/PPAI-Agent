# NFR Design — Preguntas de Clarificación — UOW-01 Capture Foundation

Estas preguntas son específicas a decisiones de patrones de diseño que no quedaron resueltas en NFR Requirements.

---

## Question 1
¿Cómo debe recibir el bot los mensajes de Telegram?

A) Webhook — Telegram envía los updates a un endpoint HTTPS del bot (requiere URL pública + TLS)
B) Long Polling — El bot consulta a Telegram periódicamente pidiendo updates (no requiere URL pública)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
¿Cómo quieres organizar la estructura del proyecto Python?

A) Layered monolith — Un solo paquete Python con módulos separados por capa (adapters/, services/, repositories/, domain/)
B) Package por feature — Un paquete por feature (capture/, common/) con capas dentro de cada uno
C) Flat — Módulos simples en raíz del proyecto, sin estructura de paquetes elaborada (scripts + módulos)
X) Other (please describe after [Answer]: tag below)

[Answer]: X Me gustaria una arquitectura de package por feature pero orientado al DDD para que sea mucho mas facil su mantenimiento.

---

## Question 3
Para el rate limiting (10 msg/min por usuario), ¿dónde prefieres mantener el estado del contador?

A) En memoria del proceso (dict en Python) — simple, se resetea al reiniciar el contenedor, suficiente para MVP personal
B) En DynamoDB con TTL — persistente entre restarts, más robusto, un read+write extra por mensaje
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 4
¿Cómo debe manejar el bot las operaciones asíncronas (DynamoDB writes, Telegram API calls)?

A) Async/await nativo de Python (asyncio) — python-telegram-bot v20+ ya es async, alinear todo el stack
B) Síncrono — usar el modo síncrono de boto3 y python-telegram-bot, más simple de razonar
X) Other (please describe after [Answer]: tag below)

[Answer]: B
