"""Tiny FastAPI-style app entrypoint for fixture tests."""

from typing import List

API_VERSION = "v1"
DEFAULT_PORT: int = 8080


def start(host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> None:
    print(f"listening on {host}:{port}")


async def shutdown() -> None:
    print("shutting down")


def _internal_helper() -> None:
    pass


class Server:
    def __init__(self, host: str):
        self.host = host

    def run(self) -> List[str]:
        return [self.host]


class _PrivateHelper:
    pass
