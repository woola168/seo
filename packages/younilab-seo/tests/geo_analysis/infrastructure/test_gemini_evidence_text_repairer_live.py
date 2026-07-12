import asyncio
import os
import re
import unicodedata
from pathlib import Path

import pytest
from pydantic import BaseModel, Field
from younilab_seo.geo_analysis.application import (
    EvidenceTextRepairCommand,
    EvidenceTextRepairFailure,
)
from younilab_seo.geo_analysis.infrastructure import (
    GeminiEvidenceTextRepairer,
    GeminiEvidenceTextRepairSettings,
)

EXPECTED_CASE_COUNT = 23
EXPECTED_FAILURE_COUNT = 46


class _LiveCase(BaseModel):
    raw_response: str = Field(alias="rawResponse", min_length=1)
    failures: list[EvidenceTextRepairFailure] = Field(min_length=1)


class _LiveFixture(BaseModel):
    cases: list[_LiveCase] = Field(min_length=1)


def test_gemini_evidence_repairer_live_historical_regression() -> None:
    fixture_path = os.getenv("GEO_EVIDENCE_REPAIR_LIVE_FIXTURE")
    if not fixture_path:
        pytest.skip("Set GEO_EVIDENCE_REPAIR_LIVE_FIXTURE to run the live regression")

    fixture = _LiveFixture.model_validate_json(
        Path(fixture_path).read_text(encoding="utf-8")
    )
    failure_count = sum(len(case.failures) for case in fixture.cases)
    assert len(fixture.cases) == EXPECTED_CASE_COUNT
    assert failure_count == EXPECTED_FAILURE_COUNT

    async def run() -> None:
        repairer = GeminiEvidenceTextRepairer(
            GeminiEvidenceTextRepairSettings.from_environment()
        )
        semaphore = asyncio.Semaphore(3)

        async def repair_case(case: _LiveCase) -> list[str]:
            async with semaphore:
                result = await repairer.repair(
                    EvidenceTextRepairCommand(
                        raw_response=case.raw_response,
                        failures=case.failures,
                    )
                )
            expected_indexes = [failure.item_index for failure in case.failures]
            actual_indexes = [repair.item_index for repair in result.repairs]
            assert actual_indexes == expected_indexes
            return [
                repair.evidence_text
                for repair in result.repairs
                if repair.evidence_text is not None
            ]

        try:
            repaired_by_case = await asyncio.gather(
                *(repair_case(case) for case in fixture.cases)
            )
        finally:
            await repairer.close()

        repaired_count = 0
        for case, repaired_evidence in zip(
            fixture.cases,
            repaired_by_case,
            strict=True,
        ):
            assert len(repaired_evidence) == len(case.failures)
            assert all(
                _normalize(evidence) in _normalize(case.raw_response)
                for evidence in repaired_evidence
            )
            repaired_count += len(repaired_evidence)
        assert repaired_count == EXPECTED_FAILURE_COUNT

    asyncio.run(run())


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip()
