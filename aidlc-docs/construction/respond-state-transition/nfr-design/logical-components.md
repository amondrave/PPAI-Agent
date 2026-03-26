# Componentes Logicos — UOW-04 Respond & State Transition

> No se introducen componentes de infraestructura nuevos. UOW-04 reutiliza toda la infra existente.

---

## Componentes reutilizados

| Componente | Tabla/Recurso | Uso en UOW-04 |
|-----------|---------------|---------------|
| Task Store | `ppai-tasks` | Leer y actualizar estado de tareas (done/snooze/clarify) |
| Event Store | `ppai-events` | Registrar InteractionEvents con TTL 90 dias |
| Cycle Store | `ppai-cycles` | Registrar eventos de interaccion a nivel de ciclo diario |
| Cache | In-memory dict | Invalidar Top 3 cache al procesar callbacks |

---

## Cambio de configuracion: TTL en ppai-events

### Estado actual
- La tabla `ppai-events` no tiene TTL habilitado.
- Los CaptureEvents (UOW-01) se almacenan indefinidamente.

### Cambio requerido
- Habilitar TTL en la tabla con atributo `ttl`.
- Agregar en Terraform:

```hcl
resource "aws_dynamodb_table" "events" {
  # ... configuracion existente ...

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}
```

- Los nuevos InteractionEvents incluyen `ttl = timestamp + 90 dias` (epoch seconds).
- Los CaptureEvents existentes sin atributo `ttl` no se eliminan (comportamiento correcto de DynamoDB TTL).

---

## Nuevo campo en ppai-tasks: snoozed_until

### Schema delta
- Agregar atributo `snoozedUntil` (ISO 8601 string) al item de DynamoDB.
- Solo presente en items con `status = snoozed`.
- No requiere GSI nuevo — el filtro es en aplicacion al momento de `list_pending`.

### Schema delta: completed_at
- Agregar atributo `completedAt` (ISO 8601 string) al item.
- Solo presente en items con `status = done`.
- Util para reportes diarios (UOW-05).

---

## Diagrama de flujo de datos

```
Usuario presiona boton
       |
       v
[Telegram] --callback_query--> [ResponseTelegramAdapter]
       |                              |
       |                     parse action + task_id
       |                              |
       v                              v
                              [ResponseService]
                                |     |     |
                          authorize   |   record events
                                |     |     |
                                v     v     v
                          [ppai-tasks] [ppai-events] [ppai-cycles]
                                |
                                v
                        invalidate_cache
                                |
                                v
                        [DecisionService._cache]
```

---

## Resumen de impacto en infraestructura

| Recurso | Cambio | Tipo |
|---------|--------|------|
| `ppai-tasks` | Nuevos atributos `snoozedUntil`, `completedAt` | Schema (sin migracion, DynamoDB schemaless) |
| `ppai-events` | Habilitar TTL, nuevo atributo `ttl` en items | Terraform + codigo |
| `ppai-cycles` | Nuevos tipos de evento en `nudgeEvents` array | Solo codigo |
| Terraform | TTL block en modulo dynamodb para events table | 4 lineas |
