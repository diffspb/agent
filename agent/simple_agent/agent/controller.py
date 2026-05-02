from __future__ import annotations

from simple_agent.agent.runtime import PrimitiveAgentRuntime, RuntimeResult
from simple_agent.storage.repository import Repository


class AgentController:
    def __init__(
        self,
        *,
        repository: Repository,
        runtime: PrimitiveAgentRuntime,
    ) -> None:
        self.repository = repository
        self.runtime = runtime

    async def start_run(self, run_id: int) -> RuntimeResult:
        run = self.repository.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        return await self.runtime.start_run(run)

    async def cancel_run(self, run_id: int) -> RuntimeResult:
        run = self.repository.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        return await self.runtime.cancel_run(run)


class RunNotFoundError(Exception):
    def __init__(self, run_id: int) -> None:
        super().__init__(f"Run not found: {run_id}")
        self.run_id = run_id
