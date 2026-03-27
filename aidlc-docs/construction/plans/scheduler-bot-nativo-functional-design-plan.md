# Plan de Functional Design — UOW-05 Scheduler Bot Nativo

## Contexto

UOW-05 pivota de "Learn, Report & Rescue" (original) a **Scheduler Bot Nativo**: recordatorios programados de inicio/cierre de día + modo zen. La visión está capturada en `aidlc-docs/scheduler-bot-nativo-vision.md`.

**Stories relacionadas**: US-09 (reporte diario), parcialmente US-06 (control intensidad/ventana).
**Nota**: US-11 (Aprendizaje conductual), US-12 (Observabilidad) quedan fuera de este UOW y se abordarán en un UOW futuro. US-10 (Rescue Mode) incluido en scope (Q1: C).

## Plan de diseño funcional

- [x] Step 1: Definir nuevos campos en `UserNudgePreferences`
- [x] Step 2: Definir lógica de recordatorio de inicio de día (Top 3 automático)
- [x] Step 3: Definir lógica de resumen de cierre de día
- [x] Step 4: Definir lógica de modo zen (activación/desactivación)
- [x] Step 5: Definir extensiones a `/config` (inicio, cierre)
- [x] Step 6: Definir nuevos comandos `/zen` y `/zen off`
- [x] Step 7: Definir reglas de negocio y validaciones
- [x] Step 8: Definir modelo de dominio y entidades actualizadas
- [x] Step 9: Generar artefactos de functional design

## Preguntas de clarificación

### Q1: Scope de UOW-05
El UOW-05 original incluía US-09/US-10/US-11/US-12 (reporte, rescue, aprendizaje, observabilidad). La visión pivota a **scheduler bot nativo** (inicio/cierre + zen). Confirma:

A) Solo scheduler bot nativo (inicio/cierre + zen) — US-09 parcial. US-10/US-11/US-12 en UOW futuro.
B) Scheduler bot nativo + reporte diario completo (US-09 full) — incluye avances/bloqueos/recomendaciones del cierre.
C) Scheduler bot nativo + US-09 + US-10 (rescue mode) — rescue se evalúa al cierre del día.

[Answer]: C

### Q2: Contenido del recordatorio de inicio
Cuando el bot envía el recordatorio matutino, ¿qué debe incluir?

A) Solo el Top 3 actual (mismo output que `/top3`).
B) Top 3 + resumen breve de lo que quedó pendiente de ayer.
C) Top 3 + mensaje motivacional breve personalizable.

[Answer]: C

### Q3: Contenido del resumen de cierre
¿Qué nivel de detalle en el resumen de fin de día?

A) Simple: conteo de completadas/pendientes/pospuestas hoy.
B) Detallado: lista de tareas completadas + pendientes + pospuestas con títulos.
C) Detallado + sugerencia: como B pero con recomendación de "con qué arrancar mañana".

[Answer]: B

### Q4: Tolerancia de timing del scheduler
El NudgeScheduler corre cada 15 min. Para recordatorios de inicio/cierre configurados a hora exacta (ej. 08:00):

A) Tolerancia ±7 min — envía si el tick cae en ventana [HH:MM - 7min, HH:MM + 7min]. Garantiza máx 1 envío por ventana.
B) Tolerancia ±15 min — más permisivo, nunca pierde un tick pero puede ser impreciso.
C) Tick dedicado — cambiar scheduler a evaluar cada minuto para inicio/cierre (más preciso, más CPU).

[Answer]: A

### Q5: Zen mode — intervalo y cap
En modo zen, ¿los nudges usan la misma lógica actual (cada 15 min, max_nudges_per_day)?

A) Sí, idéntico al comportamiento actual del NudgeScheduler. El zen solo activa/desactiva los nudges intermedios.
B) Zen con intervalo configurable separado (ej. cada 10, 15 o 30 min) y cap propio independiente del daily cap.
C) Zen idéntico al actual pero sin daily cap (mientras zen esté activo, nudges ilimitados).

[Answer]: B

### Q6: Idempotencia de recordatorios diarios
Si el bot se reinicia o hay un tick duplicado, ¿cómo evitar enviar el recordatorio de inicio/cierre dos veces en el mismo día?

A) Flag en DynamoDB: `last_start_sent_date` y `last_end_sent_date` en preferencias o ciclo del día. Verificar antes de enviar.
B) Flag en memoria del proceso (más simple pero se pierde al reiniciar — aceptable para MVP).
C) Usar el ExecutionCycle existente: registrar evento `DAILY_START_SENT` / `DAILY_END_SENT` y verificar si ya existe hoy.

[Answer]: C

### Q7: Comportamiento sin configurar
Si el usuario NO configura `inicio` ni `cierre`, ¿qué pasa?

A) No se envían recordatorios — solo nudges si zen está activo. El usuario debe configurar explícitamente.
B) Defaults: inicio 08:00, cierre 18:00 en su timezone. Se activan automáticamente al registrarse.
C) Al registrarse, el bot pregunta si quiere configurar horarios. Sin respuesta, no se envían.

[Answer]: B

### Q8: Interacción zen + silencio
Si el usuario activa zen durante su ventana de silencio (ej. zen activo pero son las 23:00 y silencio es 22:00-08:00):

A) Silencio siempre gana — zen no envía nudges dentro de la ventana de silencio.
B) Zen override — si el usuario lo activó explícitamente, confiar en su intención y enviar.

[Answer]: B
