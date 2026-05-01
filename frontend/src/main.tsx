import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type HealthState =
  | { status: "loading" }
  | { status: "ok"; app: string; environment: string }
  | { status: "error"; message: string };

function App() {
  const [health, setHealth] = useState<HealthState>({ status: "loading" });

  async function loadHealth() {
    setHealth({ status: "loading" });

    try {
      const response = await fetch("http://127.0.0.1:8000/health");
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

  useEffect(() => {
    void loadHealth();
  }, []);

  return (
    <main className="app-shell">
      <section className="toolbar">
        <div>
          <h1>Simple Agent</h1>
          <p>Проверка REST API для MVP агента.</p>
        </div>
        <button type="button" onClick={loadHealth}>
          Обновить
        </button>
      </section>

      <section className="panel">
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
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

