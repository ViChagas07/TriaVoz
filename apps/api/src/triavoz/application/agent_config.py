"""Validated agent configuration.

`extra="forbid"` keeps the room metadata predictable: the prompt builder only consumes these keys.
Bump `schema_version` when the shape changes in an incompatible way.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AgentConfigSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1, le=100)
    clinic_name: str = Field(min_length=1, max_length=120)
    greeting: str = Field(min_length=1, max_length=500)
    tone: str = Field(default="acolhedor, claro e objetivo", min_length=1, max_length=200)
    emergency_message: str = Field(
        default="Se for uma emergência, ligue agora para o SAMU, no 192.",
        min_length=1,
        max_length=300,
    )

    def as_metadata(self) -> dict[str, object]:
        return self.model_dump()
