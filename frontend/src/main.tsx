import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = "http://127.0.0.1:8000";

type HealthState =
  | { status: "loading" }
  | { status: "ok"; app: string; environment: string }
  | { status: "error"; message: string };

type Loadable<T> =
  | { status: "loading" }
  | { status: "ok"; data: T }
  | { status: "error"; message: string };

type Task = {
  id: number;
  external_id: string | null;
  type: string;
  status: string;
  title: string;
  assignee_email: string | null;
};

type Run = {
  id: number;
  task_id: number;
  status: string;
  started_at: string;
  finished_at: string | null;
  summary: string | null;
};

type Stats = {
  tasks_total: number;
  runs_total: number;
  runs_by_status: Record<string, number>;
  events_total: number;
  tool_calls_total: number;
  agent_notes_total: number;
};

function App() {
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [tasks, setTasks] = useState<Loadable<Task[]>>({ status: "loading" });
  const [runs, setRuns] = useState<Loadable<Run[]>>({ status: "loading" });
  const [stats, setStats] = useState<Loadable<Stats>>({ status: "loading" });

  async function loadHealth() {
    setHealth({ status: "loading" });

    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = await response.json();
      setHealth({
        status: "ok",
        app: payload.app,
        environment: payload.environment,
      });
    } catch (error) {
      setHealth({
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      });
    }
  }

  async function loadDashboard() {
    setTasks({ status: "loading" });
    setRuns({ status: "loading" });
    setStats({ status: "loading" });

    const load = async <T,>(path: string): Promise<T> => {
      const response = await fetch(`${API_BASE_URL}${path}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json() as Promise<T>;
    };

    try {
      const [tasksPayload, runsPayload, statsPayload] = await Promise.all([
        load<Task[]>("/api/tasks"),
        load<Run[]>("/api/runs"),
        load<Stats>("/api/stats"),
      ]);
      setTasks({ status: "ok", data: tasksPayload });
      setRuns({ status: "ok", data: runsPayload });
      setStats({ status: "ok", data: statsPayload });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setTasks({ status: "error", message });
      setRuns({ status: "error", message });
      setStats({ status: "error", message });
    }
  }

  function refreshAll() {
    void loadHealth();
    void loadDashboard();
  }

  useEffect(() => {
    refreshAll();
  }, []);

  return (
    <main className="app-shell">
      <section className="toolbar">
        <div>
          <h1>Simple Agent</h1>
          <p>Проверка REST API для MVP агента.</p>
        </div>
        <button type="button" onClick={refreshAll}>
          Обновить
        </button>
      </section>

      <section className="panel compact-panel">
        <h2>Backend Healthcheck</h2>
        {health.status === "loading" && <p className="muted">Загрузка...</p>}
        {health.status === "error" && (
          <p className="status-error">Ошибка: {health.message}</p>
        )}
        {health.status === "ok" && (
          <dl className="health-grid">
            <div>
              <dt>Статус</dt>
              <dd>{health.status}</dd>
            </div>
            <div>
              <dt>Приложение</dt>
              <dd>{health.app}</dd>
            </div>
            <div>
              <dt>Окружение</dt>
              <dd>{health.environment}</dd>
            </div>
          </dl>
        )}
      </section>

      <section className="dashboard-grid">
        <section className="panel">
          <h2>Статистика</h2>
          {stats.status === "loading" && <p className="muted">Загрузка...</p>}
          {stats.status === "error" && (
            <p className="status-error">Ошибка: {stats.message}</p>
          )}
          {stats.status === "ok" && (
            <dl className="stats-grid">
              <div>
                <dt>Задачи</dt>
                <dd>{stats.data.tasks_total}</dd>
              </div>
              <div>
                <dt>Запуски</dt>
                <dd>{stats.data.runs_total}</dd>
              </div>
              <div>
                <dt>События</dt>
                <dd>{stats.data.events_total}</dd>
              </div>
              <div>
                <dt>Вызовы инструментов</dt>
                <dd>{stats.data.tool_calls_total}</dd>
              </div>
            </dl>
          )}
        </section>

        <section className="panel">
          <h2>Статусы запусков</h2>
          {stats.status === "loading" && <p className="muted">Загрузка...</p>}
          {stats.status === "error" && (
            <p className="status-error">Ошибка: {stats.message}</p>
          )}
          {stats.status === "ok" &&
            (Object.keys(stats.data.runs_by_status).length > 0 ? (
              <ul className="status-list">
                {Object.entries(stats.data.runs_by_status).map(([status, count]) => (
                  <li key={status}>
                    <span>{status}</span>
                    <strong>{count}</strong>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">Запусков пока нет.</p>
            ))}
        </section>
      </section>

      <section className="panel">
        <h2>Задачи</h2>
        {tasks.status === "loading" && <p className="muted">Загрузка...</p>}
        {tasks.status === "error" && (
          <p className="status-error">Ошибка: {tasks.message}</p>
        )}
        {tasks.status === "ok" &&
          (tasks.data.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Внешний ID</th>
                    <th>Статус</th>
                    <th>Название</th>
                    <th>Исполнитель</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.data.map((task) => (
                    <tr key={task.id}>
                      <td>{task.id}</td>
                      <td>{task.external_id ?? "-"}</td>
                      <td>{task.status}</td>
                      <td>{task.title}</td>
                      <td>{task.assignee_email ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">Локальных задач пока нет.</p>
          ))}
      </section>

      <section className="panel">
        <h2>Запуски</h2>
        {runs.status === "loading" && <p className="muted">Загрузка...</p>}
        {runs.status === "error" && (
          <p className="status-error">Ошибка: {runs.message}</p>
        )}
        {runs.status === "ok" &&
          (runs.data.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Задача</th>
                    <th>Статус</th>
                    <th>Старт</th>
                    <th>Итог</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.data.map((run) => (
                    <tr key={run.id}>
                      <td>{run.id}</td>
                      <td>{run.task_id}</td>
                      <td>{run.status}</td>
                      <td>{formatDate(run.started_at)}</td>
                      <td>{run.summary ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">Запусков пока нет.</p>
          ))}
      </section>
    </main>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
