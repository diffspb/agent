from pathlib import Path
import sqlite3


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS agent_ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    trigger_task_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    finished_at TEXT,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_ticks_started_at ON agent_ticks(started_at);
CREATE INDEX IF NOT EXISTS idx_agent_ticks_status ON agent_ticks(status);

CREATE TABLE IF NOT EXISTS task_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick_id INTEGER NOT NULL REFERENCES agent_ticks(id) ON DELETE CASCADE,
    external_task_id TEXT NOT NULL,
    status TEXT NOT NULL,
    assignee_email TEXT,
    priority INTEGER,
    dependencies_state TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_task_candidates_tick_id ON task_candidates(tick_id);
CREATE INDEX IF NOT EXISTS idx_task_candidates_external_task_id ON task_candidates(external_task_id);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick_id INTEGER REFERENCES agent_ticks(id) ON DELETE SET NULL,
    external_task_id TEXT NOT NULL,
    branch_name TEXT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    finished_at TEXT,
    summary TEXT,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_runs_tick_id ON runs(tick_id);
CREATE INDEX IF NOT EXISTS idx_runs_external_task_id ON runs(external_task_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick_id INTEGER REFERENCES agent_ticks(id) ON DELETE CASCADE,
    run_id INTEGER REFERENCES runs(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_events_tick_id ON events(tick_id);
CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id);

CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    status TEXT NOT NULL,
    input_json TEXT NOT NULL DEFAULT '{}',
    output_json TEXT,
    error TEXT,
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_run_id ON tool_calls(run_id);

PRAGMA user_version = 2;
"""


class SqliteDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            if _needs_stage_1_schema_reset(connection):
                _drop_known_tables(connection)
            connection.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _needs_stage_1_schema_reset(connection: sqlite3.Connection) -> bool:
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version >= 2:
        return False

    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'runs'
        """
    ).fetchone()
    if row is None:
        return False

    columns = {
        str(column["name"])
        for column in connection.execute("PRAGMA table_info(runs)").fetchall()
    }
    return "task_id" in columns and "external_task_id" not in columns


def _drop_known_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS agent_notes;
        DROP TABLE IF EXISTS tool_calls;
        DROP TABLE IF EXISTS events;
        DROP TABLE IF EXISTS task_candidates;
        DROP TABLE IF EXISTS runs;
        DROP TABLE IF EXISTS tasks;
        DROP TABLE IF EXISTS agent_ticks;
        PRAGMA user_version = 0;
        """
    )
