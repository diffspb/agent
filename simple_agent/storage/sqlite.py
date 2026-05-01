from pathlib import Path
import sqlite3


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE,
    type TEXT NOT NULL DEFAULT 'task',
    status TEXT NOT NULL,
    title TEXT NOT NULL,
    author_email TEXT,
    assignee_email TEXT,
    description TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee_email ON tasks(assignee_email);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    finished_at TEXT,
    summary TEXT,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_runs_task_id ON runs(task_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

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

CREATE TABLE IF NOT EXISTS agent_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    run_id INTEGER REFERENCES runs(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_agent_notes_task_id ON agent_notes(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_notes_run_id ON agent_notes(run_id);
"""


class SqliteDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
