from __future__ import annotations

from simple_agent.llm.litellm_client import _normalize_response


def test_litellm_response_normalizes_tool_calls() -> None:
    response = {
        "choices": [
            {
                "message": {
                    "content": "Проверю файл.",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": "{\"path\": \"README.md\"}",
                            },
                        }
                    ],
                }
            }
        ]
    }

    normalized = _normalize_response(response)

    assert normalized.content == "Проверю файл."
    assert len(normalized.tool_calls) == 1
    assert normalized.tool_calls[0].name == "read_file"
    assert normalized.tool_calls[0].arguments == {"path": "README.md"}
