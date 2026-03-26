Feature: US-07 Cierre inmediato de estado por respuesta de usuario
  As a usuario final
  I want que mi respuesta actualice estado de inmediato
  So that el sistema refleje mi ejecución real

  Background:
    Given el usuario "u1" tiene una tarea en estado "nudged" con id "t1"
    And la tarea pertenece al ciclo activo del día

  Scenario: Done con confirmación — flujo completo
    When el usuario presiona el botón "Done" para la tarea "t1"
    Then el sistema pregunta "¿Confirmas que completaste esta tarea? [Sí] [No]"
    When el usuario confirma con "Sí"
    Then la tarea "t1" transiciona a estado "done"
    And se registra "completed_at" con timestamp actual
    And se invalida el cache del Top 3

  Scenario: Done cancelado — sin cambio de estado
    When el usuario presiona el botón "Done" para la tarea "t1"
    And el usuario responde "No" a la confirmación
    Then la tarea "t1" permanece en su estado original
    And no se registra evento de interacción

  Scenario: Snooze con cooldown de 1 hora
    When el usuario presiona el botón "Snooze" para la tarea "t1"
    Then la tarea "t1" transiciona a estado "snoozed"
    And "snooze_count" se incrementa en 1
    And "snoozed_until" se establece en now + 1 hora
    And la tarea no aparece en el próximo Top 3 durante el cooldown
    And se invalida el cache del Top 3

  Scenario: Snooze limit alcanzado — auto-clarify
    Given la tarea "t1" tiene "snooze_count" igual a 3
    When el usuario presiona el botón "Snooze" para la tarea "t1"
    Then el sistema responde "Ya pospusiste esta tarea 3 veces"
    And la tarea "t1" transiciona automáticamente a "needs_clarification"
    And se envía pregunta de aclaración

  Scenario: Clarify — flujo de aclaración con respuesta de texto
    When el usuario presiona el botón "Clarify" para la tarea "t1"
    Then la tarea "t1" transiciona a estado "needs_clarification"
    And el sistema envía pregunta de aclaración
    When el usuario responde con texto libre "Necesito cotizar primero"
    Then "normalized_text" se actualiza con la aclaración
    And la tarea transiciona a estado "pending"
    And "snooze_count" se resetea a 0

  Scenario: Idempotencia — doble press en Done
    Given la tarea "t1" ya está en estado "done"
    When el usuario presiona el botón "Done" para la tarea "t1"
    Then el sistema responde "Esta tarea ya fue completada"
    And no se produce cambio de estado

  Scenario: Autorización — callback de otro usuario rechazado
    When el usuario "u2" presiona el botón "Done" para la tarea "t1" del usuario "u1"
    Then el sistema responde "No tienes permiso para esta acción"
    And no se produce cambio de estado
    And se registra warning de autorización fallida
