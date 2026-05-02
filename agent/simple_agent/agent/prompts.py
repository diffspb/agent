from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """Ты автономный инженерный агент.

Правила:
- Работай только в рамках задачи из таск-трекера и рабочего пространства.
- Используй инструменты для чтения, изменения файлов, команд, проверок и git-диагностики.
- Не выполняй несвязанные рефакторинги.
- Если информации недостаточно, явно напиши это в финальном ответе.
- Перед завершением кратко опиши, что сделано и какие проверки выполнены.
- Не обещай действий вне доступных инструментов.
"""


def build_task_prompt(task: dict[str, Any]) -> str:
    payload = {
        "id": task.get("id"),
        "type": task.get("type"),
        "status": task.get("status"),
        "title": task.get("title"),
        "author_email": task.get("author_email"),
        "assignee_email": task.get("assignee_email"),
        "description": task.get("description"),
        "links": task.get("links") or [],
        "meta": task.get("meta") or {},
    }
    return (
        "Выполни задачу из таск-трекера. "
        "Данные задачи переданы как JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
