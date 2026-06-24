from datetime import datetime
from typing import Protocol
from uuid import UUID

from younilab_geo_tracking_application.contracts import (
    AnswerRequest,
    AnswerResponse,
    QueryDraft,
    QueryGenerationCommand,
    QueryResearchCommand,
    QueryResearchResult,
)


class ProviderRequestError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AnswerProvider(Protocol):
    async def generate_answer(self, request: AnswerRequest) -> AnswerResponse: ...


class QueryGenerationProvider(Protocol):
    async def generate_drafts(
        self, command: QueryGenerationCommand
    ) -> list[QueryDraft]: ...


class QueryResearchProvider(Protocol):
    async def research(self, command: QueryResearchCommand) -> QueryResearchResult: ...


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
