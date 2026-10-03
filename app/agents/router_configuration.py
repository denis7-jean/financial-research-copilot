"""Explicit configuration; Jev and shadow cannot execute with real transports."""

import os
from dataclasses import dataclass

from app.errors import ServiceFailure


@dataclass(frozen=True)
class RouterConfiguration:
    provider: str = "haiku"

    def __post_init__(self):
        if self.provider not in ("haiku", "jev", "shadow"):
            raise ServiceFailure("router", "configuration", "invalid_router_provider")

    @classmethod
    def from_environment(cls):
        return cls(os.getenv("COPILOT_ROUTER_PROVIDER", "haiku"))


def build_router(configuration=None, *, jev_transport=None):
    configuration = configuration or RouterConfiguration.from_environment()
    if configuration.provider == "shadow":
        raise ServiceFailure("router", "configuration", "router_shadow_disabled")
    if configuration.provider == "jev":
        from app.agents.jev_router import JevRouterAgent

        return JevRouterAgent(transport=jev_transport)
    if jev_transport is not None:
        raise ServiceFailure("router", "configuration", "unused_jev_transport")
    from app.agents.router import RouterAgent

    return RouterAgent()
