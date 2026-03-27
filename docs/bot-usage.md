# PPAI Bot — Guia de uso

> Personal Productivity AI: tu asistente de productividad en Telegram.

---

## Captura de tareas (texto libre)

Escribe cualquier mensaje de texto al bot y se registrara como tarea automaticamente.

```
Terminar el informe de ventas Q1
Llamar al proveedor de hosting
Revisar PR #42 del equipo frontend
```

- Limite de tareas activas: 50
- Mensajes duplicados dentro de 5 minutos se ignoran
- Rate limit: 10 mensajes por minuto

---

## Comandos disponibles

### `/top3` — Tu Top 3 de prioridades

Muestra las 3 tareas mas importantes segun el motor de scoring (urgencia, antiguedad, contexto). Cada tarea se presenta con botones de accion:

| Boton | Accion |
|-------|--------|
| **Hecho** | Marca la tarea como completada (pide confirmacion) |
| **Posponer** | Pospone la tarea 1 hora (maximo 3 veces) |
| **Aclarar** | Abre flujo de aclaracion por texto libre |

**Flujos:**
- **Done con confirmacion:** al presionar Hecho, el bot pregunta "Confirmas?" con botones `[Si] [No]`. Solo al confirmar se marca DONE.
- **Snooze con cooldown:** pospone 1 hora y muestra contador `(1/3)`. Tras el cooldown la tarea vuelve a PENDING en el siguiente `/top3`. Al 4to intento se activa aclaracion automatica.
- **Clarify:** el bot pregunta que necesitas, respondes con texto libre y la tarea se actualiza y vuelve a PENDING con snooze reseteado.

---

### `/config` — Configuracion de preferencias

Sin argumentos muestra tu configuracion actual. Subcomandos disponibles:

| Subcomando | Ejemplo | Descripcion |
|------------|---------|-------------|
| `silencio HH:MM-HH:MM` | `/config silencio 22:00-08:00` | Ventana sin recordatorios |
| `nudges N` | `/config nudges 5` | Max recordatorios/dia (1-10) |
| `timezone ZONA` | `/config timezone America/Bogota` | Zona horaria |
| `inicio HH:MM` | `/config inicio 07:30` | Hora del recordatorio matutino |
| `cierre HH:MM` | `/config cierre 19:00` | Hora del resumen de cierre |
| `zen_intervalo N` | `/config zen_intervalo 10` | Intervalo zen en minutos (5-60) |
| `zen_max N` | `/config zen_max 20` | Max nudges en modo zen (1-50) |
| `motivacion TEXTO` | `/config motivacion Hoy es tu dia` | Mensaje motivacional (max 100 chars) |

---

### `/zen` — Modo de concentracion

Activa una sesion de nudges frecuentes para cuando necesitas foco intenso.

```
/zen        — Activa modo zen
/zen off    — Desactiva modo zen
```

**Comportamiento:**
- Los nudges se envian cada `zen_intervalo` minutos (default: 15 min)
- Maximo de nudges configurado con `zen_max` (default: 10)
- Ignora la ventana de silencio mientras esta activo
- El scheduler ajusta su frecuencia automaticamente al menor intervalo zen activo

---

## Recordatorios automaticos

El bot envia recordatorios automaticos segun tu configuracion:

### Recordatorio matutino (inicio del dia)
- Se envia a la hora configurada en `/config inicio` (default: 08:00)
- Incluye tu Top 3 de prioridades y mensaje motivacional personalizado
- Se envia una sola vez por dia

### Resumen de cierre (fin del dia)
- Se envia a la hora configurada en `/config cierre` (default: 18:00)
- Lista de tareas completadas, pendientes y pospuestas
- **Rescue Mode:** si no completaste nada y quedan tareas, el bot propone una microaccion empatica

### Nudges regulares
- Recordatorios periodicos de tus tareas prioritarias
- Respetan la ventana de silencio (excepto en modo zen)
- Maximo diario configurable con `/config nudges`

---

## Valores por defecto

| Parametro | Default |
|-----------|---------|
| Zona horaria | `America/Bogota` |
| Max nudges/dia | 3 |
| Hora de inicio | 08:00 |
| Hora de cierre | 18:00 |
| Intervalo zen | 15 min |
| Max nudges zen | 10 |
| Mensaje motivacional | "A darle con todo hoy" |
| Ventana de silencio | No configurada |
