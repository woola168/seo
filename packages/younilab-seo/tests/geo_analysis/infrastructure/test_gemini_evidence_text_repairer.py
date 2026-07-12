import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest
from younilab_seo.geo_analysis.application import (
    EvidenceTextRepairCommand,
    EvidenceTextRepairFailure,
    EvidenceTextRepairUnavailable,
)
from younilab_seo.geo_analysis.infrastructure import (
    GeminiEvidenceTextRepairer,
    GeminiEvidenceTextRepairSettings,
    evidence_repair,
)


def test_gemini_evidence_repairer_resolves_block_id_to_untouched_source_text() -> None:
    async def run() -> None:
        requests: list[dict[str, Any]] = []

        async def generate_content(prompt: str) -> dict[str, Any]:
            requests.append(json.loads(prompt))
            return {
                "repairs": [
                    {
                        "itemIndex": 3,
                        "sourceBlockId": "B0001",
                    }
                ]
            }

        repairer = GeminiEvidenceTextRepairer(
            GeminiEvidenceTextRepairSettings(vertex_project="test-project"),
            generate_content=generate_content,
        )

        result = await repairer.repair(
            EvidenceTextRepairCommand(
                raw_response=(
                    "比較結果如下：\n* **Acme ERP** 適合製造業，並保留 `API` 彈性。"
                ),
                failures=[
                    EvidenceTextRepairFailure(
                        item_index=3,
                        wrong_evidence_text=("Acme ERP 適合製造業，並保留 API 彈性。"),
                    )
                ],
            )
        )

        assert result.repairs[0].item_index == 3
        assert result.repairs[0].evidence_text == (
            "* **Acme ERP** 適合製造業，並保留 `API` 彈性。"
        )
        assert requests == [
            {
                "rawResponse": (
                    "比較結果如下：\n* **Acme ERP** 適合製造業，並保留 `API` 彈性。"
                ),
                "sourceBlocks": [
                    {"sourceBlockId": "B0000", "text": "比較結果如下："},
                    {
                        "sourceBlockId": "B0001",
                        "text": "* **Acme ERP** 適合製造業，並保留 `API` 彈性。",
                    },
                ],
                "failures": [
                    {
                        "itemIndex": 3,
                        "wrongEvidenceText": ("Acme ERP 適合製造業，並保留 API 彈性。"),
                    }
                ],
            }
        ]

    asyncio.run(run())


def test_gemini_evidence_repairer_returns_none_for_unknown_source_block() -> None:
    async def run() -> None:
        async def generate_content(prompt: str) -> dict[str, Any]:
            return {
                "repairs": [
                    {
                        "itemIndex": 0,
                        "sourceBlockId": "B9999",
                    }
                ]
            }

        repairer = GeminiEvidenceTextRepairer(
            GeminiEvidenceTextRepairSettings(vertex_project="test-project"),
            generate_content=generate_content,
        )

        result = await repairer.repair(
            EvidenceTextRepairCommand(
                raw_response="**Acme ERP** 適合製造業。",
                failures=[
                    EvidenceTextRepairFailure(
                        item_index=0,
                        wrong_evidence_text="Acme ERP 適合製造業。",
                    )
                ],
            )
        )

        assert result.repairs[0].item_index == 0
        assert result.repairs[0].evidence_text is None

    asyncio.run(run())


def test_gemini_evidence_repairer_rejects_malformed_structured_output() -> None:
    async def run() -> None:
        async def generate_content(prompt: str) -> dict[str, Any]:
            return {"repairs": [{"itemIndex": 0, "unexpected": "B0000"}]}

        repairer = GeminiEvidenceTextRepairer(
            GeminiEvidenceTextRepairSettings(vertex_project="test-project"),
            generate_content=generate_content,
        )

        with pytest.raises(
            EvidenceTextRepairUnavailable,
            match="invalid structured output",
        ):
            await repairer.repair(_repair_command())

    asyncio.run(run())


def test_gemini_evidence_repairer_reuses_client_without_search_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        clients: list[Any] = []
        calls: list[dict[str, Any]] = []

        class FakeModels:
            async def generate_content(self, **kwargs: Any) -> SimpleNamespace:
                calls.append(kwargs)
                return SimpleNamespace(
                    parsed=None,
                    text='{"repairs":[{"itemIndex":0,"sourceBlockId":"B0000"}]}',
                )

        class FakeAsyncClient:
            def __init__(self) -> None:
                self.models = FakeModels()
                self.closed = False

            async def aclose(self) -> None:
                self.closed = True

        class FakeClient:
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs = kwargs
                self.aio = FakeAsyncClient()
                clients.append(self)

        monkeypatch.setattr(evidence_repair.genai, "Client", FakeClient)
        repairer = GeminiEvidenceTextRepairer(
            GeminiEvidenceTextRepairSettings(vertex_project="test-project")
        )
        command = EvidenceTextRepairCommand(
            raw_response="**Acme ERP** 適合製造業。",
            failures=[
                EvidenceTextRepairFailure(
                    item_index=0,
                    wrong_evidence_text="Acme ERP 適合製造業。",
                )
            ],
        )

        first = await repairer.repair(command)
        second = await repairer.repair(command)

        assert first == second
        assert len(clients) == 1
        assert len(calls) == 2
        assert calls[0]["config"].tools is None
        session = clients[0].kwargs["http_options"].aiohttp_client
        assert clients[0].kwargs["project"] == "test-project"
        assert not session.closed

        await repairer.close()

        assert clients[0].aio.closed
        assert session.closed

    asyncio.run(run())


def _repair_command() -> EvidenceTextRepairCommand:
    return EvidenceTextRepairCommand(
        raw_response="**Acme ERP** 適合製造業。",
        failures=[
            EvidenceTextRepairFailure(
                item_index=0,
                wrong_evidence_text="Acme ERP 適合製造業。",
            )
        ],
    )
