Feature: US-08 Registro mínimo de eventos del loop
  As a operador/admin
  I want conservar eventos clave del loop
  So that pueda auditar y analizar comportamiento

  Background:
    Given el usuario "u1" tiene una tarea en estado "nudged" con id "t1"
    And existe un ciclo activo para la fecha de hoy

  Scenario: Evento TASK_DONE registrado al completar tarea
    When el usuario confirma "Done" para la tarea "t1"
    Then se registra un InteractionEvent con event_type "TASK_DONE"
    And el evento contiene task_id "t1" y user_id "u1"
    And el evento contiene correlation_id del ciclo activo
    And se registra un cycle event en ppai-cycles

  Scenario: Evento TASK_SNOOZED registrado al posponer tarea
    When el usuario presiona "Snooze" para la tarea "t1"
    Then se registra un InteractionEvent con event_type "TASK_SNOOZED"
    And el evento contiene metadata con snooze_count actual

  Scenario: Evento TASK_CLARIFIED registrado al solicitar aclaración
    When el usuario presiona "Clarify" para la tarea "t1"
    Then se registra un InteractionEvent con event_type "TASK_CLARIFIED"

  Scenario: Evento TASK_CLARIFY_RESOLVED al responder aclaración
    Given la tarea "t1" está en estado "needs_clarification"
    When el usuario responde con texto de aclaración
    Then se registra un InteractionEvent con event_type "TASK_CLARIFY_RESOLVED"
    And el evento contiene metadata con el texto de respuesta

  Scenario: Fallo en registro de evento — best-effort sin rollback
    Given el repositorio de eventos falla al escribir
    When el usuario confirma "Done" para la tarea "t1"
    Then la tarea "t1" transiciona exitosamente a "done"
    And se registra un warning en el log
    And el estado de la tarea NO se revierte
