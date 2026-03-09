-- PPAI Database Schema v1.0
-- Convenciones:
--   - Nombres de tablas y columnas: snake_case en inglés
--   - Comentarios de negocio: español
--   - Cada tabla representa una entidad del domain model del PRD
--   - Este archivo SÍ se versiona en git (ppai.db está en .gitignore)

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA: users
-- Dominio: el freelancer/solopreneur que usa el sistema
-- Generada por: primer mensaje en Telegram
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id         TEXT    NOT NULL UNIQUE,  -- ID de usuario en Telegram
    username            TEXT,                      -- @handle opcional
    timezone            TEXT    NOT NULL DEFAULT 'America/Bogota',
    report_time         TEXT    NOT NULL DEFAULT '21:00', -- hora del reporte nocturno
    active              INTEGER NOT NULL DEFAULT 1, -- 1=activo, 0=pausado
    created_at          DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at          DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA: tasks
-- Dominio: cada intención capturada por el usuario
-- Generada por: mensaje libre en Telegram (paso CAPTURE del loop)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    raw_input           TEXT    NOT NULL,  -- texto exacto que escribió el usuario
    title               TEXT    NOT NULL,  -- título normalizado por el LLM
    task_type           TEXT    NOT NULL CHECK(task_type IN ('study','work','personal','idea','commitment')),
    energy_level        TEXT    NOT NULL CHECK(energy_level IN ('high','medium','low')),
    estimated_duration  INTEGER,           -- minutos estimados
    urgency             TEXT    NOT NULL DEFAULT 'today' CHECK(urgency IN ('today','backlog')),
    priority_rank       INTEGER,           -- 1, 2, 3 para top tasks del día; NULL = backlog
    status              TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','nudged','done','snoozed','clarifying','cancelled')),
    suggested_time      TEXT,              -- hora sugerida para ejecutar (HH:MM)
    created_at          DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at          DATETIME NOT NULL DEFAULT (datetime('now')),
    task_date           DATE    NOT NULL DEFAULT (date('now')) -- día al que pertenece la tarea
);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA: execution_cycles
-- Dominio: cada iteración del loop (EXECUTE → CONFIRM/UPDATE → LEARN)
-- Generada por: el nudge del sistema + respuesta del usuario (/done /snooze /clarify)
-- DATO CLAVE DEL MOAT: latencia, energía real, hora real de cierre
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS execution_cycles (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id                 INTEGER NOT NULL REFERENCES tasks(id),
    user_id                 INTEGER NOT NULL REFERENCES users(id),
    nudge_sent_at           DATETIME NOT NULL DEFAULT (datetime('now')),
    response_type           TEXT CHECK(response_type IN ('done','snoozed','clarified','no_response')),
    responded_at            DATETIME,
    response_latency_sec    INTEGER,   -- segundos entre nudge_sent_at y responded_at
    completion_energy       INTEGER CHECK(completion_energy IN (1,2,3)), -- 1=bajo 2=medio 3=alto
    actual_hour             INTEGER,   -- hora real del día en que se completó (0-23)
    cycle_date              DATE    NOT NULL DEFAULT (date('now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA: blocking_patterns
-- Dominio: razones por las que el usuario pospone tareas
-- Generada por: texto libre opcional al usar /snooze
-- DATO CLAVE DEL MOAT: patrones de bloqueo individuales
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS blocking_patterns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         INTEGER NOT NULL REFERENCES tasks(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    reason_text     TEXT,              -- texto libre del usuario (puede ser NULL)
    snooze_count    INTEGER NOT NULL DEFAULT 1, -- cuántas veces se posposó esta tarea
    recorded_at     DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA: daily_reports
-- Dominio: el reporte nocturno generado cada día a las 21:00
-- Generada por: el trigger automático + LLM + feedback del usuario
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_reports (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    report_date         DATE    NOT NULL,
    tasks_completed     INTEGER NOT NULL DEFAULT 0,
    tasks_snoozed       INTEGER NOT NULL DEFAULT 0,
    tasks_no_response   INTEGER NOT NULL DEFAULT 0,
    report_text         TEXT    NOT NULL, -- texto del reporte enviado al usuario
    sent_at             DATETIME,
    user_feedback       TEXT CHECK(user_feedback IN ('useful','neutral','guilty',NULL)),
    UNIQUE(user_id, report_date)          -- un reporte por usuario por día
);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLA: energy_profiles
-- Dominio: perfil circadiano del usuario (cuándo ejecuta mejor qué tipo de tarea)
-- Generada por: aggregación de execution_cycles a lo largo del tiempo
-- DATO CLAVE DEL MOAT: modelo de energía personalizado
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS energy_profiles (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    hour_of_day         INTEGER NOT NULL CHECK(hour_of_day BETWEEN 0 AND 23),
    day_of_week         INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6), -- 0=lunes
    task_type           TEXT    NOT NULL,
    avg_completion_rate REAL    NOT NULL DEFAULT 0.0, -- % de tareas completadas en este slot
    avg_energy_reported REAL    NOT NULL DEFAULT 0.0, -- energía promedio reportada
    sample_count        INTEGER NOT NULL DEFAULT 0,
    updated_at          DATETIME NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, hour_of_day, day_of_week, task_type)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- ÍNDICES — para queries frecuentes del workflow loop
-- ─────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_tasks_user_date
    ON tasks(user_id, task_date);

CREATE INDEX IF NOT EXISTS idx_tasks_status
    ON tasks(user_id, status);

CREATE INDEX IF NOT EXISTS idx_execution_cycles_task
    ON execution_cycles(task_id, cycle_date);

CREATE INDEX IF NOT EXISTS idx_blocking_patterns_user
    ON blocking_patterns(user_id, recorded_at);

CREATE INDEX IF NOT EXISTS idx_daily_reports_user_date
    ON daily_reports(user_id, report_date);
