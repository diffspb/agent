import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { App } from "./main";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("App", () => {
  test("показывает состояние загрузки", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));

    render(<App />);

    expect(screen.getByText("Backend Healthcheck")).toBeInTheDocument();
    expect(screen.getAllByText("Загрузка...").length).toBeGreaterThan(0);
  });

  test("показывает health, run, tool calls и diff artifact", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(mockFetchSuccess);

    render(<App />);

    expect(await screen.findByText("simple-agent")).toBeInTheDocument();
    expect(screen.getAllByText("PROJECT-1").length).toBeGreaterThan(0);
    expect(screen.getByText("write_file")).toBeInTheDocument();
    expect(screen.getAllByText("final.diff").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/llm-agent-summary.txt/).length).toBeGreaterThan(0);
  });

  test("показывает ошибку загрузки", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    } as Response);

    render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText("Ошибка: HTTP 500").length).toBeGreaterThan(0);
    });
  });
});

function mockFetchSuccess(input: RequestInfo | URL): Promise<Response> {
  const url = String(input);
  const payloads: Record<string, unknown> = {
    "/health": { status: "ok", app: "simple-agent", environment: "test" },
    "/api/ticks": [
      {
        id: 1,
        source: "test",
        status: "completed",
        trigger_task_id: null,
        started_at: "2026-05-02T00:00:00Z",
        finished_at: "2026-05-02T00:00:01Z",
        error: null,
      },
    ],
    "/api/runs": [
      {
        id: 1,
        tick_id: 1,
        external_task_id: "PROJECT-1",
        branch_name: null,
        status: "completed",
        started_at: "2026-05-02T00:00:00Z",
        finished_at: "2026-05-02T00:00:01Z",
        summary: "LLM runtime завершил задачу с изменениями файлов",
      },
    ],
    "/api/stats": {
      ticks_total: 1,
      task_candidates_total: 1,
      runs_total: 1,
      runs_by_status: { completed: 1 },
      events_total: 2,
      tool_calls_total: 1,
    },
    "/api/runs/1/events": [
      {
        id: 1,
        tick_id: 1,
        run_id: 1,
        type: "run.outcome",
        message: "Runtime сформировал результат выполнения",
        created_at: "2026-05-02T00:00:01Z",
      },
    ],
    "/api/runs/1/tool-calls": [
      {
        id: 1,
        run_id: 1,
        tool_name: "write_file",
        status: "completed",
        input: { path: "llm-agent-summary.txt" },
        output: { path: "llm-agent-summary.txt" },
        error: null,
        started_at: "2026-05-02T00:00:00Z",
        finished_at: "2026-05-02T00:00:01Z",
      },
    ],
    "/api/runs/1/artifacts": [{ path: "final.diff", name: "final.diff", bytes: 99 }],
    "/api/runs/1/artifacts/final.diff": {
      path: "final.diff",
      content: "--- a/llm-agent-summary.txt\n+++ b/llm-agent-summary.txt\n",
    },
    "/api/ticks/1/candidates": [
      {
        id: 1,
        tick_id: 1,
        external_task_id: "PROJECT-1",
        status: "Open",
        assignee_email: "agent@example.com",
        priority: 200,
        dependencies_state: "clear",
        decision: "selected",
        reason: "selected_highest_priority",
      },
    ],
  };

  const path = new URL(url).pathname;
  const payload = payloads[path];
  if (payload === undefined) {
    return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
  }
  return Promise.resolve({ ok: true, status: 200, json: async () => payload } as Response);
}
