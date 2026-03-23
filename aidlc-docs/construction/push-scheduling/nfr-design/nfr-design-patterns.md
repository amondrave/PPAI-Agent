# NFR Design Patterns — UOW-03 Push & Scheduling

> Patrones base de resiliencia, logging, configuración y capas se heredan de UOW-01/UOW-02.
> Este documento define los patrones delta nuevos de UOW-03.

---

## DP-PUSH-01: Single In-Process Scheduler Pattern

### Pattern
UOW-03 usa un **scheduler in-process** dentro del mismo contenedor del bot. No se
crea worker separado ni scheduler administrado.

### Design
- Un solo componente interno ejecuta:
  - tick periódico;
  - evaluación de elegibilidad;
  - construcción del nudge;
  - dispatch y retries.

### Benefits
- Menor complejidad operativa.
- Menor costo.
- Menor cantidad de piezas móviles en MVP.

### Accepted Tradeoff
- Si el contenedor cae, también cae la capacidad proactiva de push.
- No existe aislamiento fuerte entre runtime reactivo y runtime del scheduler.

---

## DP-PUSH-02: Persisted Dispatch Marker Pattern

### Pattern
Para evitar duplicados dentro del mismo proceso, el scheduler marca el intento de
dispatch en `ExecutionCycle` **antes** de enviar, y valida ese estado antes de cada
intento.

### Design
```text
1. Resolver cycle activo
2. Verificar si ya existe marca de dispatch para user/ventana/task
3. Si no existe, persistir marca `NUDGE_SCHEDULED`
4. Proceder con el envio
5. Actualizar a `NUDGE_SENT` o `NUDGE_FAILED`
```

### Benefits
- Evita duplicados por reentrada lógica dentro del mismo proceso.
- Reusa persistencia ya existente del ciclo/event log.
- No requiere locks distribuidos ni infraestructura adicional.

### Constraint
- No garantiza idempotencia fuerte frente a reinicios del contenedor.

---

## DP-PUSH-03: Product Default Timezone Pattern

### Pattern
Si el usuario no tiene timezone configurada, el scheduler usa una timezone default del
producto:

```text
America/Bogota
```

### Benefits
- Permite operar desde el día uno sin bloquear nudges por configuración incompleta.
- Simplifica el MVP para el contexto inicial del producto.

### Risk
- Un usuario fuera de esa zona podría recibir un horario menos óptimo.

### Mitigation
- Persistir `timezone` en `ppai-preferences` y permitir override futuro.

---

## DP-PUSH-04: Cross-Midnight Silence Window Pattern

### Pattern
La ventana de silencio soporta rangos que cruzan medianoche.

### Design
Ejemplos válidos:
- `09:00 -> 12:00`
- `22:00 -> 07:00`

### Validation Rule
- Si `start < end`: ventana normal en el mismo día.
- Si `start > end`: ventana cruza medianoche y se interpreta como dos segmentos
  lógicos continuos.

### Benefit
- Modela mejor el comportamiento real de descanso/trabajo sin requerir múltiples
  ventanas por día.

---

## DP-PUSH-05: Fixed Short Backoff Retry Pattern

### Pattern
El dispatch usa **backoff fijo corto** para los 3 intentos del MVP.

### Design
```text
attempt #1 -> inmediato
attempt #2 -> +30s
attempt #3 -> +30s
```

### Benefits
- Comportamiento simple y predecible.
- Fácil de testear.
- Compatible con estrategia lean sin scheduler complejo.

### Tradeoff
- Menos adaptativo que un backoff incremental o exponencial.

---

## DP-PUSH-06: Fail-Soft Dispatch Pattern

### Pattern
Si el envío falla definitivamente, el sistema **no rompe el loop general**.

### Design
- Registrar `NUDGE_FAILED`
- Loggear contexto suficiente
- Continuar con el resto del sistema sin reintento global del tick

### Benefit
- Aísla la falla de Telegram del resto de capacidades del bot.
- Evita que una operación outbound degrade captura u otras interacciones.

---

## DP-PUSH-07: Dual-Layer Callback Authorization Pattern

### Pattern
La validación de owner en callbacks se aplica en dos capas:

1. **Chequeo temprano** en el adapter de Telegram.
2. **Validación defensiva** en el servicio de aplicación.

### Benefits
- Falla rápido antes de entrar al flujo de negocio.
- Mantiene seguridad incluso si otro caller invoca el servicio sin pasar por Telegram.
- Reduce riesgo de IDOR o mutaciones sobre recursos ajenos.

### Rule
```text
callback.from_user.id debe coincidir con el user_id dueño del recurso
```

---

## DP-PUSH-08: Minimal Correlation Logging Pattern

### Pattern
Los eventos del scheduler usan correlación explícita con:

- `cycle_id`
- `task_id`

No se introduce `dispatch_id` separado en MVP.

### Benefit
- Correlación suficiente para operar y depurar.
- Menor complejidad de identifiers adicionales.

### Applied to
- `NUDGE_SCHEDULED`
- `NUDGE_SENT`
- `NUDGE_SKIPPED_ACTIVITY`
- `NUDGE_FAILED`

---

## Security Compliance Summary (Baseline Extension — UOW-03)

| Rule | Status | Notas |
|---|---|---|
| SECURITY-01 Encryption | Compliant (heredado) | `ppai-preferences` debe ir cifrada |
| SECURITY-03 App Logging | Compliant | Correlación por `cycle_id` + `task_id`, sin payload sensible |
| SECURITY-05 Input Validation | Compliant | Validación de ventanas y callbacks |
| SECURITY-06 Least Privilege | Compliant | Sin infraestructura extra pesada, IAM delta acotado |
| SECURITY-08 App Access Control | Compliant | Patrón dual-layer de autorización |
| SECURITY-11 Secure Design | Compliant | Fail-soft, lean scheduler, protección anti-duplicado |
| SECURITY-15 Exception Handling | Compliant | Fallos outbound se contienen y registran |
