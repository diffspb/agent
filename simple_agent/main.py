import uvicorn


def main() -> None:
    uvicorn.run(
        "simple_agent.service.asgi:app",
        host="127.0.0.1",
        port=8010,
        reload=False,
    )


if __name__ == "__main__":
    main()
