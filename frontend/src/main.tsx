import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = "http://127.0.0.1:8010";

type HealthState =
  | { status: "loading" }
  | { status: "ok"; app: string; environment: string }
  | { status: "error"; message: string };

type Loadable<T> =
  | { status: "loading" }
  | { status: "ok"; data: T }
  | { status: "error"; message: string };

type AgentTick = {
  id: number;
  source: string;
  status: string;
  trigger_task_id: string | null;
  started_at: string;
  finished_at: string | null;
  error: string | null;
};

type Run = {
  id: number;
  tick_id: number | null;
  external_task_id: string;
  branch_name: string | null;
  status: string;
  started_at: string;
  finished_at: string | null;
  summary: string | null;
};

type RunEvent = {
  id: number;
  tick_id: number | null;
  run_id: number | null;
  type: string;
  message: string;
  created_at: string;
};

type ToolCall = {
  id: number;
  run_id: number;
  tool_name: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: string | null;
  started_at: string;
  finished_at: string | null;
};

type RunArtifact = {
  path: string;
  name: string;
  bytes: number;
};

type TaskCandidate = {
  id: number;
  tick_id: number;
  external_task_id: string;
  status: string;
  assignee_email: string | null;
  priority: number | null;
  dependencies_state: string;
  decision: string;
  reason: string | null;
};

type TickRunResult = {
  tick: AgentTick;
  selected_run: Run | null;
  candidates: TaskCandidate[];
};

type Stats = {
  ticks_total: number;
  task_candidates_total: number;
  runs_total: number;
  runs_by_status: Record<string, number>;
  events_total: number;
  tool_calls_total: number;
};

export function App() {
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [ticks, setTicks] = useState<Loadable<AgentTick[]>>({ status: "loading" });
  const [runs, setRuns] = useState<Loadable<Run[]>>({ status: "loading" });
  const [stats, setStats] = useState<Loadable<Stats>>({ status: "loading" });
  const [candidates, setCandidates] = useState<Loadable<TaskCandidate[]>>({
    status: "loading",
  });
  const [events, setEvents] = useState<Loadable<RunEvent[]>>({
    status: "loading",
  });
  const [toolCalls, setToolCalls] = useState<Loadable<ToolCall[]>>({
    status: "loading",
  });
  const [artifacts, setArtifacts] = useState<Loadable<RunArtifact[]>>({
    status: "loading",
  });
  const [artifactContent, setArtifactContent] = useState<Loadable<string>>({
    status: "loading",
  });
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [tickAction, setTickAction] = useState<
    { status: "idle" } | { status: "running" } | { status: "error"; message: string }
  >({ status: "idle" });
  const [runAction, setRunAction] = useState<
    { status: "idle" } | { status: "running"; runId: number } | { status: "error"; message: string }
  >({ status: "idle" });

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

  async function loadDashboard(preferredRunId?: number | null) {
    setTicks({ status: "loading" });
    setRuns({ status: "loading" });
    setStats({ status: "loading" });
    setCandidates({ status: "loading" });
    setEvents({ status: "loading" });
    setToolCalls({ status: "loading" });
    setArtifacts({ status: "loading" });
    setArtifactContent({ status: "loading" });

    const load = async <T,>(path: string): Promise<T> => {
      const response = await fetch(`${API_BASE_URL}${path}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json() as Promise<T>;
    };

    try {
      const [ticksPayload, runsPayload, statsPayload] = await Promise.all([
        load<AgentTick[]>("/api/ticks"),
        load<Run[]>("/api/runs"),
        load<Stats>("/api/stats"),
      ]);
      setTicks({ status: "ok", data: ticksPayload });
      setRuns({ status: "ok", data: runsPayload });
      setStats({ status: "ok", data: statsPayload });
      const effectiveRunId = preferredRunId ?? selectedRunId;
      const runForEvents = effectiveRunId
        ? runsPayload.find((run) => run.id === effectiveRunId)
        : runsPayload[0];
      if (runForEvents) {
        setSelectedRunId(runForEvents.id);
        const [eventsPayload, toolCallsPayload, artifactsPayload] = await Promise.all([
          load<RunEvent[]>(`/api/runs/${runForEvents.id}/events`),
          load<ToolCall[]>(`/api/runs/${runForEvents.id}/tool-calls`),
          load<RunArtifact[]>(`/api/runs/${runForEvents.id}/artifacts`),
        ]);
        setEvents({ status: "ok", data: eventsPayload });
        setToolCalls({ status: "ok", data: toolCallsPayload });
        setArtifacts({ status: "ok", data: artifactsPayload });
        const diffArtifact = artifactsPayload.find((artifact) => artifact.path === "final.diff");
        if (diffArtifact) {
          const artifactPayload = await load<{ content: string }>(
            `/api/runs/${runForEvents.id}/artifacts/${encodeURIComponent(diffArtifact.path)}`,
          );
          setArtifactContent({ status: "ok", data: artifactPayload.content });
        } else {
          setArtifactContent({ status: "ok", data: "" });
        }
      } else {
        setSelectedRunId(null);
        setEvents({ status: "ok", data: [] });
        setToolCalls({ status: "ok", data: [] });
        setArtifacts({ status: "ok", data: [] });
        setArtifactContent({ status: "ok", data: "" });
      }
      if (ticksPayload.length > 0) {
        const candidatesPayload = await load<TaskCandidate[]>(
          `/api/ticks/${ticksPayload[0].id}/candidates`,
        );
        setCandidates({ status: "ok", data: candidatesPayload });
      } else {
        setCandidates({ status: "ok", data: [] });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setTicks({ status: "error", message });
      setRuns({ status: "error", message });
      setStats({ status: "error", message });
      setCandidates({ status: "error", message });
      setEvents({ status: "error", message });
      setToolCalls({ status: "error", message });
      setArtifacts({ status: "error", message });
      setArtifactContent({ status: "error", message });
    }
  }

  async function runTick() {
    setTickAction({ status: "running" });
    try {
      const response = await fetch(`${API_BASE_URL}/api/agent/tick`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: "frontend" }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = (await response.json()) as TickRunResult;
      setCandidates({ status: "ok", data: payload.candidates });
      setTickAction({ status: "idle" });
      await loadDashboard(payload.selected_run?.id);
    } catch (error) {
      setTickAction({
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      });
    }
  }

  async function runLifecycleAction(runId: number, action: "start" | "cancel") {
    setRunAction({ status: "running", runId });
    try {
      const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/${action}`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      setRunAction({ status: "idle" });
      await loadDashboard(runId);
    } catch (error) {
      setRunAction({
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      });
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
        <div className="toolbar-actions">
          <button type="button" onClick={runTick} disabled={tickAction.status === "running"}>
            {tickAction.status === "running" ? "Запуск..." : "Запустить tick"}
          </button>
          <button type="button" onClick={refreshAll}>
            Обновить
          </button>
        </div>
      </section>
      {tickAction.status === "error" && (
        <section className="panel compact-panel">
          <p className="status-error">Ошибка запуска tick: {tickAction.message}</p>
        </section>
      )}
      {runAction.status === "error" && (
        <section className="panel compact-panel">
          <p className="status-error">Ошибка действия с run: {runAction.message}</p>
        </section>
      )}

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
                <dt>Tick</dt>
                <dd>{stats.data.ticks_total}</dd>
              </div>
              <div>
                <dt>Кандидаты</dt>
                <dd>{stats.data.task_candidates_total}</dd>
              </div>
              <div>
                <dt>Запуски</dt>
                <dd>{stats.data.runs_total}</dd>
              </div>
              <div>
                <dt>События</dt>
                <dd>{stats.data.events_total}</dd>
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
        <h2>Tick</h2>
        {ticks.status === "loading" && <p className="muted">Загрузка...</p>}
        {ticks.status === "error" && (
          <p className="status-error">Ошибка: {ticks.message}</p>
        )}
        {ticks.status === "ok" &&
          (ticks.data.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Источник</th>
                    <th>Статус</th>
                    <th>Задача</th>
                    <th>Старт</th>
                    <th>Ошибка</th>
                  </tr>
                </thead>
                <tbody>
                  {ticks.data.map((tick) => (
                    <tr key={tick.id}>
                      <td>{tick.id}</td>
                      <td>{tick.source}</td>
                      <td>{tick.status}</td>
                      <td>{tick.trigger_task_id ?? "-"}</td>
                      <td>{formatDate(tick.started_at)}</td>
                      <td>{tick.error ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">Tick-событий пока нет.</p>
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
                    <th>Tick</th>
                    <th>Задача</th>
                    <th>Ветка</th>
                    <th>Статус</th>
                    <th>Старт</th>
                    <th>Итог</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.data.map((run) => (
                    <tr
                      key={run.id}
                      className={run.id === selectedRunId ? "selected-row" : undefined}
                      onClick={() => void loadDashboard(run.id)}
                    >
                      <td>{run.id}</td>
                      <td>{run.tick_id ?? "-"}</td>
                      <td>{run.external_task_id}</td>
                      <td>{run.branch_name ?? "-"}</td>
                      <td>{run.status}</td>
                      <td>{formatDate(run.started_at)}</td>
                      <td>{run.summary ?? "-"}</td>
                      <td>
                        <div className="table-actions">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              void runLifecycleAction(run.id, "start");
                            }}
                            disabled={
                              run.status !== "queued" ||
                              (runAction.status === "running" && runAction.runId === run.id)
                            }
                          >
                            Старт
                          </button>
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              void runLifecycleAction(run.id, "cancel");
                            }}
                            disabled={
                              !["queued", "running"].includes(run.status) ||
                              (runAction.status === "running" && runAction.runId === run.id)
                            }
                          >
                            Отмена
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">Запусков пока нет.</p>
          ))}
      </section>

      <section className="panel">
        <h2>События run</h2>
        {events.status === "loading" && <p className="muted">Загрузка...</p>}
        {events.status === "error" && (
          <p className="status-error">Ошибка: {events.message}</p>
        )}
        {events.status === "ok" &&
          (events.data.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Время</th>
                    <th>Тип</th>
                    <th>Сообщение</th>
                  </tr>
                </thead>
                <tbody>
                  {events.data.map((event) => (
                    <tr key={event.id}>
                      <td>{formatDate(event.created_at)}</td>
                      <td>{event.type}</td>
                      <td>{event.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">Событий выбранного run пока нет.</p>
          ))}
      </section>

      <section className="panel">
        <h2>Вызовы tools</h2>
        {toolCalls.status === "loading" && <p className="muted">Загрузка...</p>}
        {toolCalls.status === "error" && (
          <p className="status-error">Ошибка: {toolCalls.message}</p>
        )}
        {toolCalls.status === "ok" &&
          (toolCalls.data.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Время</th>
                    <th>Tool</th>
                    <th>Статус</th>
                    <th>Вход</th>
                    <th>Ошибка</th>
                  </tr>
                </thead>
                <tbody>
                  {toolCalls.data.map((toolCall) => (
                    <tr key={toolCall.id}>
                      <td>{formatDate(toolCall.started_at)}</td>
                      <td>{toolCall.tool_name}</td>
                      <td>{toolCall.status}</td>
                      <td>
                        <code>{compactJson(toolCall.input)}</code>
                      </td>
                      <td>{toolCall.error ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">Вызовов tools выбранного run пока нет.</p>
          ))}
      </section>

      <section className="panel">
        <h2>Артефакты run</h2>
        {artifacts.status === "loading" && <p className="muted">Загрузка...</p>}
        {artifacts.status === "error" && (
          <p className="status-error">Ошибка: {artifacts.message}</p>
        )}
        {artifacts.status === "ok" &&
          (artifacts.data.length > 0 ? (
            <>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Файл</th>
                      <th>Размер</th>
                    </tr>
                  </thead>
                  <tbody>
                    {artifacts.data.map((artifact) => (
                      <tr key={artifact.path}>
                        <td>{artifact.path}</td>
                        <td>{artifact.bytes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {artifactContent.status === "ok" && artifactContent.data && (
                <pre className="artifact-preview">{artifactContent.data}</pre>
              )}
              {artifactContent.status === "error" && (
                <p className="status-error">Ошибка чтения артефакта: {artifactContent.message}</p>
              )}
            </>
          ) : (
            <p className="muted">Артефактов выбранного run пока нет.</p>
          ))}
      </section>

      <section className="panel">
        <h2>Кандидаты последнего tick</h2>
        {candidates.status === "loading" && <p className="muted">Загрузка...</p>}
        {candidates.status === "error" && (
          <p className="status-error">Ошибка: {candidates.message}</p>
        )}
        {candidates.status === "ok" &&
          (candidates.data.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Задача</th>
                    <th>Статус</th>
                    <th>Решение</th>
                    <th>Причина</th>
                    <th>Приоритет</th>
                    <th>Зависимости</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.data.map((candidate) => (
                    <tr key={candidate.id}>
                      <td>{candidate.external_task_id}</td>
                      <td>{candidate.status}</td>
                      <td>{candidate.decision}</td>
                      <td>{candidate.reason ?? "-"}</td>
                      <td>{candidate.priority ?? "-"}</td>
                      <td>{candidate.dependencies_state}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">Кандидатов пока нет.</p>
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

function compactJson(value: unknown) {
  const text = JSON.stringify(value);
  return text.length > 90 ? `${text.slice(0, 90)}...` : text;
}

if (!import.meta.env.TEST) {
  createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}
