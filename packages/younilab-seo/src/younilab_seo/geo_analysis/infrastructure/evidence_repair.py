import json
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiohttp
from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field

from younilab_seo.geo_analysis.application import (
    EvidenceTextRepair,
    EvidenceTextRepairCommand,
    EvidenceTextRepairResult,
    EvidenceTextRepairUnavailable,
)

EVIDENCE_REPAIR_SYSTEM_PROMPT = (
    "You locate source evidence for a GEO (Generative Engine Optimization) "
    "semantic analysis pipeline.\n"
    "For every input failure, select the sourceBlockId whose text directly "
    "supports it.\n"
    "Do not repair, regenerate, summarize, or classify any semantic fact.\n"
    "Never rewrite or copy source text into the output. Return only IDs that "
    "exist in sourceBlocks. Prefer the block containing the same claim even "
    "when wrongEvidenceText omits Markdown or changes terminal punctuation. "
    "Return null when no block directly supports the failed evidence. Never "
    "use knowledge outside rawResponse."
)


class _GeminiEvidenceRepair(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    item_index: int = Field(
        alias="itemIndex",
        ge=0,
        description="Copy the itemIndex of the failed evidence being repaired.",
    )
    source_block_id: str | None = Field(
        alias="sourceBlockId",
        description=(
            "Copy the ID of the single source block that directly supports the "
            "failed evidence. Return null when no source block supports it."
        ),
    )


class _GeminiEvidenceRepairOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    repairs: list[_GeminiEvidenceRepair] = Field(
        description=(
            "Return exactly one repair for every input failure and preserve "
            "the input order."
        )
    )


@dataclass(frozen=True)
class GeminiEvidenceTextRepairSettings:
    vertex_project: str = ""
    vertex_location: str = "global"
    credentials_path: str = ""
    model: str = "gemini-3.1-flash-lite"
    temperature: float = 0.0
    thinking_level: str = "medium"
    timeout_seconds: float = 60.0

    @classmethod
    def from_environment(cls) -> "GeminiEvidenceTextRepairSettings":
        return cls(
            vertex_project=(
                os.getenv("VERTEX_AI_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT", "")
            ),
            vertex_location=os.getenv("VERTEX_AI_LOCATION", "global"),
            credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
            model=os.getenv(
                "GEO_EVIDENCE_REPAIR_MODEL",
                os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
            ),
            temperature=float(os.getenv("GEO_EVIDENCE_REPAIR_TEMPERATURE", "0")),
            thinking_level=os.getenv(
                "GEO_EVIDENCE_REPAIR_THINKING_LEVEL",
                os.getenv("GEMINI_THINKING_LEVEL", "medium"),
            ),
            timeout_seconds=float(
                os.getenv("GEO_EVIDENCE_REPAIR_TIMEOUT_SECONDS", "60")
            ),
        )

    def resolve_vertex_project(self) -> str:
        if self.vertex_project:
            return self.vertex_project
        if not self.credentials_path:
            return ""
        path = Path(self.credentials_path)
        if not path.is_file():
            return ""
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ""
        project_id = payload.get("project_id")
        return project_id if isinstance(project_id, str) else ""


GenerateContent = Callable[[str], Awaitable[dict[str, Any]]]


@dataclass
class GeminiEvidenceTextRepairer:
    settings: GeminiEvidenceTextRepairSettings
    generate_content: GenerateContent | None = None
    _session: aiohttp.ClientSession | None = field(default=None, init=False, repr=False)
    _client: genai.Client | None = field(default=None, init=False, repr=False)

    async def repair(
        self,
        command: EvidenceTextRepairCommand,
    ) -> EvidenceTextRepairResult:
        blocks = _source_blocks(command.raw_response)
        prompt = _repair_prompt(command, blocks)
        output = await self._generate_output(prompt)
        block_text_by_id = {block["sourceBlockId"]: block["text"] for block in blocks}
        return EvidenceTextRepairResult(
            repairs=[
                EvidenceTextRepair(
                    item_index=repair.item_index,
                    evidence_text=block_text_by_id.get(repair.source_block_id or ""),
                )
                for repair in output.repairs
            ]
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aio.aclose()
            self._client = None
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _generate_output(self, prompt: str) -> _GeminiEvidenceRepairOutput:
        if self.generate_content is not None:
            try:
                return _GeminiEvidenceRepairOutput.model_validate(
                    await self.generate_content(prompt)
                )
            except (TypeError, ValueError) as exc:
                raise EvidenceTextRepairUnavailable(
                    "Gemini evidence repair returned invalid structured output"
                ) from exc

        try:
            response = await self._get_client().aio.models.generate_content(
                model=self.settings.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.settings.temperature,
                    system_instruction=EVIDENCE_REPAIR_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=_GeminiEvidenceRepairOutput,
                    thinking_config=types.ThinkingConfig(
                        thinking_level=self.settings.thinking_level.upper(),
                    ),
                ),
            )
            if isinstance(response.parsed, _GeminiEvidenceRepairOutput):
                return response.parsed
            return _GeminiEvidenceRepairOutput.model_validate_json(
                response.text or "{}"
            )
        except EvidenceTextRepairUnavailable:
            raise
        except Exception as exc:
            raise EvidenceTextRepairUnavailable(
                "Gemini evidence repair is unavailable"
            ) from exc

    def _get_client(self) -> genai.Client:
        if self._client is not None:
            return self._client
        project_id = self.settings.resolve_vertex_project()
        if not project_id:
            raise EvidenceTextRepairUnavailable(
                "Vertex AI project is required for evidence repair"
            )
        if self.settings.credentials_path:
            os.environ.setdefault(
                "GOOGLE_APPLICATION_CREDENTIALS",
                self.settings.credentials_path,
            )
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.settings.timeout_seconds)
            )
        self._client = genai.Client(
            vertexai=True,
            project=project_id,
            location=self.settings.vertex_location,
            http_options=types.HttpOptions(aiohttp_client=self._session),
        )
        return self._client


def _source_blocks(raw_response: str) -> list[dict[str, str]]:
    return [
        {"sourceBlockId": f"B{index:04d}", "text": line}
        for index, line in enumerate(raw_response.splitlines())
        if line.strip()
    ]


def _repair_prompt(
    command: EvidenceTextRepairCommand,
    blocks: list[dict[str, str]],
) -> str:
    return json.dumps(
        {
            "rawResponse": command.raw_response,
            "sourceBlocks": blocks,
            "failures": [
                failure.model_dump(mode="json", by_alias=True)
                for failure in command.failures
            ],
        },
        ensure_ascii=False,
        indent=2,
    )
