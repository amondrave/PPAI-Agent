# Logical Components — UOW-03 Push & Scheduling

> Componentes lógicos nuevos o extendidos para UOW-03. Se integran con `capture/`
> y `decision/` sin crear un nuevo servicio separado.

---

## Estructura lógica propuesta

```text
ppai/
  push/
    application/
      nudge_scheduler.py          # tick in-process cada 15 min
      nudge_service.py            # evaluación + construcción + dispatch
      ports.py                    # PreferencesRepo, CycleEventRepo, TelegramPushPort
    domain/
      entities.py                 # NudgeDispatch, UserNudgePreferences
      value_objects.py            # WindowEvaluation, DispatchOutcome
      exceptions.py               # PushError hierarchy
    infrastructure/
      dynamodb_preferences_repo.py
      cycle_event_repo.py         # adaptación sobre cycles/events existentes
      telegram_push_adapter.py    # outbound sender
```

> El nombre exacto del paquete puede ajustarse en code planning, pero funcionalmente
> estos componentes deben existir.

---

## Componente: NudgeScheduler

| Atributo | Valor |
|---|---|
| Tipo | Scheduler in-process |
| Frecuencia | Cada 15 minutos |
| Responsabilidad | Disparar la evaluación periódica de ventanas |

### Notas
- No decide política de negocio compleja fuera de iniciar el tick.
- No necesita conocer detalles de Telegram.
- Invoca al servicio principal de push.

---

## Componente: NudgeService

| Atributo | Valor |
|---|---|
| Tipo | Application Service |
| Responsabilidad | Ejecutar la evaluación completa del push y el dispatch |

### Responsabilidades concretas
- cargar preferencias del usuario;
- resolver timezone operativa;
- verificar ventana de silencio;
- verificar actividad reciente;
- verificar límite diario;
- resolver Top 3 vigente;
- tomar tarea objetivo (#1);
- registrar `NUDGE_SCHEDULED`;
- enviar vía Telegram;
- actualizar estado final (`sent`, `failed`, `skipped`).

### Observación
- Según tu decisión, este servicio centraliza evaluación y envío; no se separa en
  evaluator y dispatcher distintos en MVP.

---

## Componente: PreferencesRepository

| Atributo | Valor |
|---|---|
| Tipo | Port |
| Persistencia | DynamoDB `ppai-preferences` |
| Access pattern principal | `get(user_id)` / `save(preferences)` |

### Rol
- Leer/escribir `timezone`
- Leer/escribir `maxNudgesPerDay`
- Leer/escribir `silenceStart` / `silenceEnd`

---

## Componente: CycleEventRepository

| Atributo | Valor |
|---|---|
| Tipo | Port/adapter |
| Persistencia | `ppai-cycles` + event log existente |
| Rol | Registrar eventos de dispatch y consultar marcas previas |

### Responsabilidades
- verificar si ya existe dispatch previo para la ventana actual;
- registrar `NUDGE_SCHEDULED`;
- registrar `NUDGE_SENT`;
- registrar `NUDGE_SKIPPED_ACTIVITY`;
- registrar `NUDGE_FAILED`.

### Anti-duplicado
- Es el componente que materializa la marca persistida antes del envío.

---

## Componente: TelegramPushAdapter

| Atributo | Valor |
|---|---|
| Tipo | Outbound adapter |
| Rol | Enviar mensajes de nudge por Telegram |

### Responsabilidades
- construir payload compatible con Telegram;
- enviar mensaje con botones inline;
- retornar éxito/fallo al servicio de aplicación;
- no tomar decisiones de negocio.

---

## Componente: CallbackAuthorizationGuard

| Atributo | Valor |
|---|---|
| Tipo | Guard lógico transversal |
| Ubicación | Adapter + servicio |
| Rol | Validar ownership del callback |

### Regla
- El adapter corta temprano callbacks inválidos.
- El servicio vuelve a validar defensivamente antes de mutar estado.

---

## Flujo lógico principal

```text
NudgeScheduler.tick()
  -> NudgeService.run_tick()
     -> PreferencesRepository.get(user_id)
     -> resolver timezone (fallback America/Bogota)
     -> evaluar silencio / actividad / límite
     -> CycleEventRepository.check_existing_dispatch(...)
     -> obtener Top 3 vigente
     -> CycleEventRepository.record_scheduled(...)
     -> TelegramPushAdapter.send(...)
     -> CycleEventRepository.record_sent|failed|skipped(...)
```

---

## Dependencias hacia bounded contexts existentes

| Dependencia | Uso |
|---|---|
| `decision` | Obtener Top 3 vigente / tarea #1 priorizada |
| `capture` | Leer/actualizar `TaskState` cuando una tarea pase a `nudged` |
| `shared` | Config, logging estructurado, utilidades de tiempo |

---

## Fronteras de responsabilidad

### UOW-03 sí hace
- scheduling;
- evaluación de elegibilidad;
- dispatch proactivo;
- update `prioritized -> nudged`;
- trazabilidad de intentos.

### UOW-03 no hace
- completar el flujo de `done` / `snooze` / `clarify` como negocio completo;
- cerrar el ciclo diario;
- recalcular aprendizaje conductual.

---

## Decisiones de simplicidad explícitas

| Tema | Decisión |
|---|---|
| Scheduler | 1 componente in-process |
| Evaluador/dispatcher | No se separan en MVP |
| Anti-duplicado | Marca persistida en ciclo |
| Correlación | `cycle_id` + `task_id` |
| Infra extra | Ninguna pesada |
