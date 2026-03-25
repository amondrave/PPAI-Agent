Feature: US-05 Nudge accionable en Telegram
  As a usuario final
  I want recibir nudges con opciones directas (done, snooze, clarify)
  So that pueda responder rápido sin fricción cognitiva

  Background:
    Given el usuario "u1" tiene tareas prioritizadas
    And existe un Top 3 vigente con tarea "#1" siendo "Enviar propuesta al cliente"

  Scenario: Nudge enviado exitosamente con botones inline
    Given el scheduler evalúa la ventana de las 09:00
    And el usuario no tuvo actividad en los últimos 60 minutos
    When el scheduler ejecuta el tick
    Then se envía un nudge a Telegram con el título "Enviar propuesta al cliente"
    And el nudge contiene botones "done", "snooze", "clarify"
    And la tarea objetivo transiciona a estado "nudged"
    And se registra el evento "NUDGE_SENT" en el ciclo

  Scenario: Nudge sin Top 3 disponible - no se envía
    Given no existe Top 3 vigente para el usuario
    When el scheduler ejecuta el tick
    Then no se envía ningún mensaje a Telegram
    And se registra el motivo "skipped_no_top3"

  Scenario: Reintento controlado ante fallo transitorio de Telegram
    Given el primer intento de envío falla con error transitorio
    When el scheduler ejecuta el tick
    Then se realizan hasta 3 intentos de envío
    And si el segundo intento tiene éxito se registra "NUDGE_SENT"

  Scenario: Fallo definitivo después de 3 intentos
    Given todos los intentos de envío a Telegram fallan
    When el scheduler ejecuta el tick
    Then se registra el evento "NUDGE_FAILED" con el motivo del error
    And la tarea no cambia de estado

  Scenario: Re-engagement por inactividad mayor a 24 horas
    Given el usuario lleva más de 24 horas sin actividad en el loop
    When el scheduler evalúa el tick
    Then se envía un nudge de baja intensidad con una sola tarea
    And el tono del mensaje es motivacional suave sin presión
